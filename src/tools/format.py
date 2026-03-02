"""Formatting and schema validation helpers for sales briefings."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List


def validate_briefing(briefing: Dict[str, object]) -> None:
    """Minimal runtime validation without external dependencies."""
    for key in ["company", "generated_at", "news", "industry_context", "talking_points"]:
        if key not in briefing:
            raise ValueError(f"Missing required field: {key}")

    if not isinstance(briefing["company"], str) or not briefing["company"].strip():
        raise ValueError("company must be a non-empty string")

    datetime.fromisoformat(str(briefing["generated_at"]).replace("Z", "+00:00"))

    news = briefing["news"]
    if not isinstance(news, list) or len(news) < 1:
        raise ValueError("news must be a non-empty list")
    for item in news:
        for field in ["title", "source", "published", "url", "summary"]:
            if field not in item:
                raise ValueError(f"news item missing field: {field}")

    ctx = briefing["industry_context"]
    for field in ["industry", "trends", "ad_opportunities"]:
        if field not in ctx:
            raise ValueError(f"industry_context missing field: {field}")

    points = briefing["talking_points"]
    if not isinstance(points, list) or not (2 <= len(points) <= 3):
        raise ValueError("talking_points must contain 2-3 items")


def to_markdown(briefing: Dict[str, object]) -> str:
    news_lines: List[str] = []
    for item in briefing["news"]:
        news_lines.append(
            f"- **{item['title']}** ({item['source']}, {item['published']})\n"
            f"  - {item['summary']}\n"
            f"  - {item['url']}"
        )

    trend_lines = "\n".join([f"- {x}" for x in briefing["industry_context"]["trends"]])
    opp_lines = "\n".join([f"- {x}" for x in briefing["industry_context"]["ad_opportunities"]])
    point_lines = "\n".join([f"- {x}" for x in briefing["talking_points"]])

    return f"""# Sales Briefing: {briefing['company']}

_Generated at: {briefing['generated_at']}_

## 1) Recent Company News
{chr(10).join(news_lines)}

## 2) Industry Context
**Industry snapshot:** {briefing['industry_context']['industry']}

**Key trends**
{trend_lines}

**Digital ad opportunities**
{opp_lines}

## 3) Tailored Talking Points (for Sanoma media sales)
{point_lines}
"""