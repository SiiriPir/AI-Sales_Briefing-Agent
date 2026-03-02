# AI Sales Briefing Agent

A lightweight agent that takes a company name and returns a **structured sales briefing** for a media sales representative at **Sanoma**.

The briefing includes:
1. Recent company news
2. Industry context
3. 2-3 tailored digital advertising talking points

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run:

```bash
python -m src.main "Spotify"
```

JSON output:

```bash
python -m src.main "Spotify" --json
```

Write to file:

```bash
python -m src.main "Spotify" --out briefing.md
```

## Project structure

```text
src/
  main.py                    # CLI entrypoint
  agent.py                   # CLI orchestration
  prompts/brief_v1.txt       # System prompt for LLM talking points
  schemas/briefing.schema.json
  tools/
    news.py                  # Google News RSS ingestion
    industry.py              # Wikipedia-based company/industry context
    summarization.py         # OpenAI + fallback talking-point generation
    format.py                # Markdown formatter + schema validation
tests/
  test_briefing.py
```

## Solution design writeup

### 1) Data gathering
- **Company news**: `src/tools/news.py` queries Google News RSS with the company name, normalizes title/source/date/url, and returns the most recent items.
- **Industry context**: `src/tools/industry.py` fetches Wikipedia page summary for the company name (when available) as a lightweight profile proxy.
- **Reliability fallback**: if Wikipedia is unavailable, the agent still returns a generic but usable context and ad-market trends.

### 2) LLM prompting approach
- Prompt template is stored in `src/prompts/brief_v1.txt`.
- The model receives structured JSON containing `company`, `news`, and `industry_context`.
- It is instructed to return **only a JSON array** with 2-3 concise, practical talking points.
- By default, the app uses OpenAI (`gpt-4o-mini`) when `OPENAI_API_KEY` is set.
- If no API key is available (or model call fails), it falls back to deterministic rule-based talking points so the CLI remains fully functional.

### 3) Output structure
- The final object is validated against `src/schemas/briefing.schema.json`.
- Required fields:
  - `company`
  - `generated_at`
  - `news[]` (title, source, published, url, summary)
  - `industry_context` (industry, trends, ad_opportunities)
  - `talking_points` (2-3 items)
- The CLI can render either:
  - **Markdown** for human-readable sales prep
  - **JSON** for downstream automation

## Environment variables

- `OPENAI_API_KEY` (optional): enables LLM-generated talking points.
- `OPENAI_MODEL` (optional): defaults to `gpt-4o-mini`.

## Tests

```bash
pytest
```

Covers schema validation, markdown formatting, and fallback talking-point generation.