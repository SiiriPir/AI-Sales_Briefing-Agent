"""Core agent orchestration for building structured sales briefings."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any, Dict

from .tools.format import to_markdown, validate_briefing
from .tools.industry import build_industry_context
from .tools.news import fetch_company_news
from .tools.summarization import generate_talking_points, summarize_news_snippets


@dataclass(frozen=True)
class AgentConfig:
    """Runtime configuration for the sales briefing agent."""

    news_limit: int = 5
    company_name_for_pitch: str = "Sanoma"


class SalesBriefingAgent:
    """Builds and renders structured sales briefings for a target company."""

    def __init__(self, config: AgentConfig | None = None) -> None:
        self.config = config or AgentConfig()

    def build_briefing(self, company: str) -> Dict[str, Any]:
        """Build a validated briefing dictionary for a single company."""
        news = fetch_company_news(company, limit=self.config.news_limit)
        if not news:
            news = [
                {
                    "title": f"No live news retrieved for {company}",
                    "source": "Local fallback",
                    "published": dt.date.today().isoformat(),
                    "url": "N/A",
                    "summary": "Network-restricted environment prevented live news retrieval; use this as a placeholder signal.",
                }
            ]

        news = summarize_news_snippets(news)
        industry_context = build_industry_context(company)
        talking_points = generate_talking_points(company, news, industry_context)

        briefing: Dict[str, Any] = {
            "company": company,
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "news": news,
            "industry_context": industry_context,
            "talking_points": talking_points[:3],
        }
        validate_briefing(briefing)
        return briefing

    def render_markdown(self, briefing: Dict[str, Any]) -> str:
        """Render briefing dict into markdown."""
        return to_markdown(briefing)