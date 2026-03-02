import datetime as dt

from src.tools.format import to_markdown, validate_briefing
from src.tools.summarization import _fallback_talking_points


def _sample_briefing():
    return {
        "company": "Example Corp",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "news": [
            {
                "title": "Example Corp launches new service",
                "source": "Example News",
                "published": "2026-01-01",
                "url": "https://example.com/news",
                "summary": "Example News reports that Example Corp launches new service.",
            }
        ],
        "industry_context": {
            "industry": "Example Corp is a technology company",
            "trends": ["Performance marketing is growing."],
            "ad_opportunities": ["Contextual display around relevant content."],
        },
        "talking_points": [
            "Lead with a contextual test campaign tied to the product launch.",
            "Offer measurable KPI reporting to demonstrate ROI quickly.",
        ],
    }


def test_validate_schema_passes():
    validate_briefing(_sample_briefing())


def test_markdown_contains_sections():
    md = to_markdown(_sample_briefing())
    assert "# Sales Briefing: Example Corp" in md
    assert "## 1) Recent Company News" in md
    assert "## 3) Tailored Talking Points" in md


def test_fallback_talking_points_count():
    points = _fallback_talking_points(
        "Example Corp",
        news=[{"title": "Headline"}],
        industry_context={"trends": ["Trend"], "ad_opportunities": ["Opportunity"]},
    )
    assert 2 <= len(points) <= 3


def test_agent_build_briefing_with_fallback_news(monkeypatch):
    from src.agent import SalesBriefingAgent

    monkeypatch.setattr("src.agent.fetch_company_news", lambda company, limit=5: [])
    monkeypatch.setattr(
        "src.agent.build_industry_context",
        lambda company: {
            "industry": "Tech",
            "trends": ["Trend"],
            "ad_opportunities": ["Opportunity"],
        },
    )
    monkeypatch.setattr(
        "src.agent.generate_talking_points",
        lambda company, news, industry_context: ["Point 1", "Point 2"],
    )

    agent = SalesBriefingAgent()
    briefing = agent.build_briefing("Example Corp")

    assert briefing["company"] == "Example Corp"
    assert briefing["news"][0]["source"] == "Local fallback"
    assert len(briefing["talking_points"]) == 2


def test_load_env_file_sets_missing_values(tmp_path, monkeypatch):
    from src.tools.summarization import _load_env_file

    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=test_key\nOPENAI_MODEL=test_model\n", encoding="utf-8")

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    _load_env_file(env_file)

    assert __import__("os").environ["OPENAI_API_KEY"] == "test_key"
    assert __import__("os").environ["OPENAI_MODEL"] == "test_model"


def test_load_env_file_does_not_override_existing(tmp_path, monkeypatch):
    from src.tools.summarization import _load_env_file

    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=file_key\n", encoding="utf-8")

    monkeypatch.setenv("OPENAI_API_KEY", "existing_key")
    _load_env_file(env_file)

    assert __import__("os").environ["OPENAI_API_KEY"] == "existing_key"
    assert __import__("os").environ["OPENAI_API_KEY"] == "existing_key"