"""Project paths and shared constants."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
CACHE = DATA / "cache"
PROCESSED = DATA / "processed"

DB_PATH = DATA / "label_lens.duckdb"

# Polite identifier for the open data hosts that ask for one (OFF, Wikidata).
USER_AGENT = "LabelLens/0.1 (AIEC capstone; arnaud.everything@gmail.com)"

# The four jurisdictions we track legal status across, kept separate from hazard.
JURISDICTIONS = ("EU", "US_FDA", "US_CA", "IARC")

for _d in (RAW, CACHE, PROCESSED):
    _d.mkdir(parents=True, exist_ok=True)
