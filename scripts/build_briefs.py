"""Generate the per-additive intelligence briefs (the RAG corpus).

    uv run python scripts/build_briefs.py

Needs OPENROUTER_API_KEY in .env.local. Writes one markdown brief per additive
to data/briefs/. Identity and Regulatory-status sections come straight from the
store; the Evidence narrative is written by the LLM from those same facts.
"""
from __future__ import annotations

from label_lens.briefs.generate import BRIEFS_DIR, build_all
from label_lens import llm


def main() -> None:
    if not llm.is_configured():
        print("OPENROUTER_API_KEY is not set. Add it to .env.local, e.g.:")
        print('  echo "OPENROUTER_API_KEY=sk-or-..." >> .env.local')
        print("Then re-run: uv run python scripts/build_briefs.py")
        return
    n = build_all()
    print(f"wrote {n} briefs to {BRIEFS_DIR}")


if __name__ == "__main__":
    main()
