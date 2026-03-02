"""CLI entrypoint for AI Sales Briefing Agent."""

from __future__ import annotations

import argparse
import json
import sys

from .agent import SalesBriefingAgent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a structured AI sales briefing.")
    parser.add_argument("company", help="Company name to brief")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of markdown")
    parser.add_argument("--out", help="Optional file path to save output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    agent = SalesBriefingAgent()

    try:
        briefing = agent.build_briefing(args.company)
    except Exception as exc:  # pragma: no cover - CLI safety
        print(f"Error generating briefing: {exc}", file=sys.stderr)
        return 1

    output = json.dumps(briefing, indent=2) if args.json else agent.render_markdown(briefing)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(output)
    else:
        print(output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())