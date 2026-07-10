"""Load the gold evaluation set (evals/gold.jsonl)."""
from __future__ import annotations

import json

from label_lens.config import ROOT

GOLD_PATH = ROOT / "evals" / "gold.jsonl"


def load_gold(lane: str | None = None) -> list[dict]:
    rows = [json.loads(line) for line in GOLD_PATH.read_text().splitlines() if line.strip()]
    return [r for r in rows if lane is None or r["lane"] == lane]
