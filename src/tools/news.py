"""Minimal Google News RSS fetcher for company briefing input."""

from __future__ import annotations

import datetime as dt
import logging
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
DEFAULT_LIMIT = 5


@dataclass(frozen=True)
class NewsItem:
    """Normalized news item from Google News RSS."""

    title: str
    url: str
    source: str
    published_at: Optional[dt.datetime]
    snippet: Optional[str] = None


def fetch_google_news(company_name: str, limit: int = DEFAULT_LIMIT) -> List[NewsItem]:
    """Fetch top Google News RSS entries for a company."""
    query = urllib.parse.quote(company_name)
    rss_url = GOOGLE_NEWS_RSS.format(query=query)
    logger.info("google_news_rss_request url=%s company=%s", rss_url, company_name)

    try:
        req = urllib.request.Request(rss_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:  # nosec B310
            xml_text = resp.read().decode("utf-8", errors="ignore")
    except Exception as exc:
        logger.warning("google_news_rss_failed company=%s error=%s", company_name, exc)
        return []

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.warning("google_news_rss_parse_failed company=%s error=%s", company_name, exc)
        return []

    items: List[NewsItem] = []
    seen_urls: set[str] = set()
    for node in root.findall("./channel/item"):
        parsed = _parse_rss_item(node)
        if not parsed:
            continue
        if parsed.url in seen_urls:
            continue
        seen_urls.add(parsed.url)
        items.append(parsed)

    items.sort(key=lambda x: x.published_at or dt.datetime.min.replace(tzinfo=dt.timezone.utc), reverse=True)
    logger.info("google_news_rss_parsed company=%s count=%s", company_name, len(items))
    return items[:limit]


def fetch_company_news(company: str, limit: int = DEFAULT_LIMIT) -> List[Dict[str, str]]:
    """Backward-compatible API used by the agent.

    Returns list-of-dicts with keys: title/source/published/url/summary.
    """
    items = fetch_google_news(company, limit=limit)
    results: List[Dict[str, str]] = []
    for item in items:
        results.append(
            {
                "title": item.title,
                "source": item.source,
                "published": item.published_at.date().isoformat() if item.published_at else "",
                "url": item.url,
                "summary": item.snippet or "",
            }
        )
    return results


def _parse_rss_item(node: ET.Element) -> Optional[NewsItem]:
    """Parse an RSS item into a NewsItem."""
    raw_title = (node.findtext("title") or "").strip()
    link = (node.findtext("link") or "").strip()
    pub_date = (node.findtext("pubDate") or "").strip()
    description = (node.findtext("description") or "").strip() or None

    if not raw_title or not link:
        return None

    source = "Google News"
    title = raw_title

    # Google News commonly appends source to title: "Headline - Publisher"
    if " - " in raw_title:
        head, tail = raw_title.rsplit(" - ", 1)
        if head.strip():
            title = head.strip()
        if tail.strip():
            source = tail.strip()

    return NewsItem(
        title=title,
        url=link,
        source=source,
        published_at=_parse_datetime(pub_date),
        snippet=description,
    )


def _parse_datetime(raw: str) -> Optional[dt.datetime]:
    """Parse RSS date into timezone-aware UTC datetime when possible."""
    if not raw:
        return None
    try:
        parsed = parsedate_to_datetime(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc)
    except Exception:
        return None


def debug_run() -> None:
    """Quick local debug execution for Google News RSS."""
    company = "Spotify"
    for idx, item in enumerate(fetch_google_news(company, limit=5), start=1):
        print(f"{idx}. {item.title}")
        print(f"   source={item.source}")
        print(f"   published={item.published_at}")
        print(f"   url={item.url}")


if __name__ == "__main__":
    debug_run()