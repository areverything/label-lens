"""Ask the Label Lens agent a question from the command line.

Usage:
    uv run python scripts/ask.py "Is E171 banned in the EU?"
    uv run python scripts/ask.py --user alice "Am I over any safe limit today?"

Requires OPENROUTER_API_KEY in .env.local. Set a LangSmith key to see traces.
"""
from __future__ import annotations

import argparse

from label_lens.agent.graph import answer


def main() -> None:
    ap = argparse.ArgumentParser(description="Ask the Label Lens agent.")
    ap.add_argument("question", help="the question to ask")
    ap.add_argument("--user", default="demo", help="user id (for memory)")
    args = ap.parse_args()
    print(answer(args.question, user_id=args.user))


if __name__ == "__main__":
    main()
