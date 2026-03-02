"""Industry context builder grounded in Wikipedia + recent news signals."""

from __future__ import annotations

import json
import logging
import re
import urllib.parse
import urllib.request
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

COMPANY_TYPES = [
    "B2B enterprise tech",
    "B2C consumer platform",
    "Retail / ecommerce",
    "Financial services",
    "Media / publishing",
    "Other",
]

TYPE_KEYWORDS = {
    "B2B enterprise tech": [
        "enterprise",
        "software",
        "cloud",
        "saas",
        "gpu",
        "semiconductor",
        "data center",
        "ai chips",
        "platform",
        "developer",
    ],
    "B2C consumer platform": [
        "streaming",
        "music",
        "podcast",
        "audiobook",
        "subscription",
        "creator",
        "consumer",
        "users",
        "mobile app",
    ],
    "Retail / ecommerce": ["retail", "ecommerce", "shopping", "marketplace", "store", "merchandise"],
    "Financial services": ["bank", "payments", "fintech", "insurance", "asset management", "credit"],
    "Media / publishing": ["publisher", "publishing", "newsroom", "broadcast", "media company", "advertising"],
}

TRENDS_BY_TYPE: Dict[str, List[str]] = {
    "B2B enterprise tech": [
        "Enterprise buyers are prioritizing AI-enabled productivity and automation use cases.",
        "Marketing budgets are concentrating on measurable pipeline impact and account-level targeting.",
        "Co-marketing partnerships are increasingly used to build trust in complex buying cycles.",
    ],
    "B2C consumer platform": [
        "Audience growth is tied to retention, engagement depth, and subscription value perception.",
        "Creator-led and culturally relevant campaigns are outperforming broad generic messaging.",
        "Ad-supported tiers and performance storytelling are shaping monetization strategy.",
    ],
    "Retail / ecommerce": [
        "Retail brands are balancing margin pressure with customer acquisition efficiency.",
        "Seasonal and event-driven campaigns are being optimized with faster creative iteration.",
        "First-party audience segments are central to conversion-focused media planning.",
    ],
    "Financial services": [
        "Trust, compliance, and clarity are core themes in financial customer communication.",
        "Product education campaigns are increasingly personalized by customer lifecycle stage.",
        "Performance media is being paired with brand investment to improve conversion quality.",
    ],
    "Media / publishing": [
        "Content portfolio strategy is closely linked to subscription and ad revenue mix.",
        "Publishers are packaging premium audience segments for higher-value ad demand.",
        "Cross-platform distribution is critical for sustaining reach and engagement quality.",
    ],
    "Other": [
        "Commercial teams are under pressure to prove marketing efficiency and business outcomes.",
        "Partnership and ecosystem plays are becoming more important growth levers.",
        "Audience strategy is shifting toward stronger first-party insight and targeting.",
    ],
}

OPPORTUNITIES_BY_TYPE: Dict[str, List[str]] = {
    "B2B enterprise tech": [
        "Run account-focused campaigns in decision-maker contexts tied to AI and infrastructure topics.",
        "Bundle thought-leadership content with retargeting to move mid-funnel prospects toward demo actions.",
        "Use co-branded partner campaigns to expand credibility in priority verticals.",
    ],
    "B2C consumer platform": [
        "Activate contextual campaigns around entertainment, creator, and lifestyle moments.",
        "Launch audience segments for lapsed-user re-engagement and premium-tier upsell.",
        "Pair high-reach video with conversion-focused retargeting for subscription growth.",
    ],
    "Retail / ecommerce": [
        "Align media bursts with seasonal demand windows and category-level intent signals.",
        "Use dynamic creative and product storytelling to improve add-to-cart conversion rates.",
        "Design full-funnel plans linking awareness placements to performance retargeting.",
    ],
    "Financial services": [
        "Build trust-first campaigns using premium editorial environments and educational messaging.",
        "Segment audiences by financial life events for more relevant product communication.",
        "Use incrementality measurement to validate cross-channel spend efficiency.",
    ],
    "Media / publishing": [
        "Package premium content adjacency campaigns for advertisers seeking high-quality attention.",
        "Promote subscriptions with sequential messaging across awareness and conversion formats.",
        "Use audience intelligence to create sponsor-ready vertical bundles.",
    ],
    "Other": [
        "Run contextual campaigns in high-intent content environments relevant to the brand category.",
        "Test cross-channel media packages with clear KPI and lift measurement plans.",
        "Use phased pilots to identify the strongest audience-message combinations quickly.",
    ],
}


def build_industry_context(company: str, news: Optional[List[Dict[str, object]]] = None) -> Dict[str, object]:
    """Build company-specific industry context from wiki baseline + news signals."""
    wiki_summary = _fetch_wikipedia_summary(company)
    company_type = classify_company(company, wiki_summary, news)

    industry = _build_industry_summary(company, company_type, wiki_summary)
    trends = list(TRENDS_BY_TYPE.get(company_type, TRENDS_BY_TYPE["Other"]))
    opportunities = list(OPPORTUNITIES_BY_TYPE.get(company_type, OPPORTUNITIES_BY_TYPE["Other"]))

    extra_trends = _news_signal_trends(news, company_type)
    for trend in extra_trends:
        if trend not in trends:
            trends.insert(0, trend)
    trends = trends[:3]

    logger.info("industry_context_selected company=%s type=%s trends=%s", company, company_type, trends)
    return {
        "industry": industry,
        "trends": trends,
        "ad_opportunities": opportunities[:3],
    }


def classify_company(company: str, wiki_summary: str, news: Optional[List[Dict[str, object]]] = None) -> str:
    """Classify company type using deterministic keyword matches."""
    text = f"{wiki_summary} {_flatten_news_text(news)}".lower()
    scores: Dict[str, int] = {ctype: 0 for ctype in COMPANY_TYPES}

    for ctype, keywords in TYPE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                scores[ctype] += 1

    selected = max(scores, key=scores.get)
    if scores[selected] == 0:
        selected = "Other"

    logger.info("industry_classification company=%s selected=%s scores=%s", company, selected, scores)
    return selected


def _build_industry_summary(company: str, company_type: str, wiki_summary: str) -> str:
    """Build a concise 1-2 sentence business model summary."""
    if wiki_summary:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", wiki_summary) if s.strip()]
        selected = " ".join(sentences[:2]).strip()
        return selected[:300] if len(selected) > 300 else selected

    if company_type == "Other":
        return (
            f"{company} operates across a mixed business model where growth depends on product-market fit, "
            "customer demand, and commercial execution."
        )

    article = "an" if company_type.lower().startswith(("a", "e", "i", "o", "u")) else "a"
    return (
        f"{company} is primarily {article} {company_type.lower()} business with growth tied to audience, product, "
        "and commercial execution in its core markets."
    )


def _news_signal_trends(news: Optional[List[Dict[str, object]]], company_type: str) -> List[str]:
    """Inject 1-2 simple trends derived from recent headlines/snippets."""
    text = _flatten_news_text(news).lower()
    trends: List[str] = []

    if any(k in text for k in ["partnership", "partner"]):
        trends.append("Partnership momentum suggests stronger co-marketing and brand activation opportunities.")
    if "earnings" in text:
        trends.append("Recent earnings narratives indicate heightened pressure to show measurable growth outcomes.")
    if company_type == "B2B enterprise tech" and any(k in text for k in ["healthcare ai", "data center", "ai chips"]):
        trends.append("Vertical AI adoption signals (e.g., healthcare or data center use cases) are accelerating enterprise demand.")

    return trends[:2]


def _flatten_news_text(news: Optional[List[Dict[str, object]]]) -> str:
    """Join title + snippet fields from news list into a single text block."""
    if not news:
        return ""
    parts: List[str] = []
    for item in news:
        title = str(item.get("title", ""))
        snippet = str(item.get("summary", item.get("snippet", "")))
        parts.append(f"{title} {snippet}")
    return " ".join(parts)


def _fetch_wikipedia_summary(company: str) -> str:
    """Fetch Wikipedia summary extract for a company title."""
    title = urllib.parse.quote(company.replace(" ", "_"))
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:  # nosec B310
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
        return str(data.get("extract", ""))
    except Exception:
        return ""