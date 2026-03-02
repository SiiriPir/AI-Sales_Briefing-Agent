"""Summarization and talking-point generation with optional OpenAI HTTP call + fallback."""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import Dict, List


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
    _load_env_file(ENV_PATH)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _fallback_talking_points(company, news, industry_context)

    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    payload = {
        "company": company,
        "news": news,
        "industry_context": industry_context,
    }

    endpoint = "https://api.openai.com/v1/responses"
    body = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "input": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(payload)},
        ],
        "temperature": 0.7,
    }

    try:
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
        text = data.get("output_text", "").strip()
        points = json.loads(text)
        if isinstance(points, list) and 2 <= len(points) <= 3:
            return [str(p) for p in points]
    except Exception:
        pass

    return _fallback_talking_points(company, news, industry_context)


def _load_env_file(path: Path) -> None:
    """Load simple KEY=VALUE pairs from a .env file into process env.

    Existing environment variables are not overwritten.
    """
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[len("export "):].strip()
        if "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
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