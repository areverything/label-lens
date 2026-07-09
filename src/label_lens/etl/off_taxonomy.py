"""Load the Open Food Facts additives taxonomy.

The taxonomy is the front half of the spine: it maps E-number -> name, class,
colour index, EFSA evaluation, and (for ~82% of entries) a Wikidata QID. It does
NOT carry CAS numbers, so the QID is our bridge to CAS (see wikidata.py).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import httpx

from label_lens.config import RAW, USER_AGENT

TAXONOMY_URL = "https://static.openfoodfacts.org/data/taxonomies/additives.json"
TAXONOMY_PATH = RAW / "off_additives_taxonomy.json"


@dataclass(frozen=True)
class OffAdditive:
    e_number: str            # bare digits form, e.g. "171"
    name_en: str | None
    additives_classes: list[str]
    colour_index: str | None
    wikidata_qid: str | None
    efsa_evaluation_url: str | None
    efsa_adi: str | None


def download(force: bool = False) -> Path:
    """Fetch the taxonomy JSON to data/raw if missing."""
    if TAXONOMY_PATH.exists() and not force:
        return TAXONOMY_PATH
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=60, follow_redirects=True) as c:
        r = c.get(TAXONOMY_URL)
        r.raise_for_status()
        TAXONOMY_PATH.write_bytes(r.content)
    return TAXONOMY_PATH


def _en(field: dict | None) -> str | None:
    """Pull the English value from a {'en': ...} language map."""
    if not field:
        return None
    return field.get("en")


def _classes(field: dict | None) -> list[str]:
    raw = _en(field) or ""
    # e.g. "en:colour" or "en:antioxidant, en:preservative"
    return [c.strip().removeprefix("en:") for c in raw.split(",") if c.strip()]


def load() -> dict[str, OffAdditive]:
    """Parse the taxonomy into {bare-e-number -> OffAdditive}."""
    path = download()
    raw = json.loads(path.read_text())
    out: dict[str, OffAdditive] = {}
    for entry in raw.values():
        e = _en(entry.get("e_number"))
        if not e:
            continue
        qid = _en(entry.get("wikidata"))
        out[e] = OffAdditive(
            e_number=e,
            name_en=_en_name(entry),
            additives_classes=_classes(entry.get("additives_classes")),
            colour_index=_en(entry.get("colour_index")),
            wikidata_qid=qid,
            efsa_evaluation_url=_en(entry.get("efsa_evaluation_url")),
            efsa_adi=_en(entry.get("efsa_evaluation_adi")),
        )
    return out


def _en_name(entry: dict) -> str | None:
    """The taxonomy name map has per-language 'E102 - Tartrazine' strings.

    Prefer the English one, else fall back to any value, and strip the leading
    'E### - ' prefix so we keep just the substance name.
    """
    name = entry.get("name") or {}
    val = name.get("en") or next(iter(name.values()), None)
    if not val:
        return None
    if " - " in val:
        val = val.split(" - ", 1)[1]
    return val.strip()
