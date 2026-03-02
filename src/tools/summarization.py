"""Summarization and talking-point generation with optional OpenAI HTTP call + fallback."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "brief_v1.txt"
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


def summarize_news_snippets(news_items: List[Dict[str, str]]) -> List[Dict[str, str]]:
    for item in news_items:
        title = item.get("title", "").strip()
        source = item.get("source", "Unknown source")
        if title:
            lead = title[0].lower() + title[1:] if len(title) > 1 else title.lower()
            item["summary"] = f"{source} reports that {lead}."
        else:
            item["summary"] = f"Recent coverage from {source} may indicate evolving priorities."
    return news_items


def generate_talking_points(company: str, news: List[Dict[str, str]], industry_context: Dict[str, object]) -> List[str]:
    api_key = _resolve_api_key()
    if not api_key:
        logger.info("openai_api_key_missing_using_fallback")
        return _fallback_talking_points(company, news, industry_context)

    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    payload = {
        "company": company,
        "news": news,
        "industry_context": industry_context,
    }

    try:
        content = _call_openai_chat(prompt, payload, api_key)
        points = _parse_points_json(content)
        if isinstance(points, list) and len(points) >= 2:
            return [str(p) for p in points[:3]]

        logger.warning("openai_response_unparsable_using_fallback")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")[:400]
        logger.warning("openai_http_error status=%s body=%s", exc.code, body)
    except Exception as exc:
        logger.warning("openai_generation_failed_using_fallback error=%s", exc)

    return _fallback_talking_points(company, news, industry_context)


def _call_openai_chat(prompt: str, payload: Dict[str, object], api_key: str) -> str:
    """Call OpenAI Chat Completions and return assistant text content."""
    endpoint = "https://api.openai.com/v1/chat/completions"
    body = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(payload)},
        ],
        "temperature": 0.3,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "talking_points_response",
                "schema": {
                    "type": "object",
                    "properties": {
                        "talking_points": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 2,
                            "maxItems": 3,
                        }
                    },
                    "required": ["talking_points"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
        },
    }

    request = urllib.request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310
        data = json.loads(response.read().decode("utf-8", errors="ignore"))

    choices = data.get("choices", [])
    if not isinstance(choices, list) or not choices:
        return ""

    message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
    content = message.get("content", "") if isinstance(message, dict) else ""
    return str(content).strip()


def _parse_points_json(raw_text: str) -> Optional[List[str]]:
    """Parse talking points from JSON array or object payload."""
    if not raw_text.strip():
        return None

    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json", "", 1).strip()

    try:
        parsed = json.loads(cleaned)
    except Exception:
        return None

    if isinstance(parsed, list):
        return [str(p) for p in parsed]

    if isinstance(parsed, dict):
        points = parsed.get("talking_points")
        if isinstance(points, list):
            return [str(p) for p in points]

    return None


def _resolve_api_key() -> Optional[str]:
    """Resolve API key from environment and .env locations."""
    current = os.getenv("OPENAI_API_KEY", "").strip()
    if current:
        return current

    _load_env_file(ENV_PATH)
    _load_env_file(Path.cwd() / ".env")

    resolved = os.getenv("OPENAI_API_KEY", "").strip()
    if resolved:
        logger.info("openai_api_key_resolved_from_env")
    return resolved or None


def _load_env_file(path: Path) -> None:
    """Load simple KEY=VALUE pairs from a .env file into process env.

    Existing non-empty environment variables are preserved.
    """
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[len("export "):].strip()
        if "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip()

        if value and value[0] not in {'"', "'"}:
            value = value.split(" #", 1)[0].strip()

        value = value.strip('"').strip("'")

        if not key:
            continue

        current = os.environ.get(key, "")
        if current.strip():
            continue
        os.environ[key] = value


def _fallback_talking_points(company: str, news: List[Dict[str, str]], industry_context: Dict[str, object]) -> List[str]:
    first_headline = news[0]["title"] if news else f"recent developments at {company}"
    trend = industry_context.get("trends", ["Measurable media performance is increasingly important."])[0]
    opportunity = industry_context.get("ad_opportunities", ["Cross-channel packages can improve reach and conversion."])[0]

    return [
        f"Use {first_headline} as a campaign hook and propose timely contextual placements across premium digital inventory.",
        f"Position Sanoma as a performance partner: {trend}",
        f"Start with a 6-8 week pilot focused on {str(opportunity).lower()} with clear KPI tracking (reach, CTR, and conversion lift).",
    ]