"""Resolve Wikidata QIDs to CAS numbers and E-numbers.

This is the CAS bridge. The OFF taxonomy gives us a QID per additive; Wikidata
carries P231 (CAS Registry Number) and P628 (E number). We fetch both so the
join can (a) key everything on CAS and (b) cross-validate the E-number the QID
claims against the E-number the taxonomy claims.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import httpx

from label_lens.config import USER_AGENT

API = "https://www.wikidata.org/w/api.php"
P_CAS = "P231"
P_ENUM = "P628"


@dataclass
class WikidataChem:
    qid: str
    cas_numbers: list[str] = field(default_factory=list)   # in Wikidata preferred/normal order
    e_numbers: list[str] = field(default_factory=list)


def _string_claims(claims: dict, prop: str) -> list[str]:
    out = []
    for c in claims.get(prop, []):
        snak = c.get("mainsnak", {})
        if snak.get("snaktype") != "value":
            continue
        val = snak.get("datavalue", {}).get("value")
        if isinstance(val, str):
            out.append(val)
    return out


def fetch(qids: list[str]) -> dict[str, WikidataChem]:
    """Batch-resolve QIDs (Wikidata allows up to 50 per wbgetentities call)."""
    out: dict[str, WikidataChem] = {}
    uniq = [q for q in dict.fromkeys(qids) if q]
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=60) as c:
        for i in range(0, len(uniq), 50):
            batch = uniq[i : i + 50]
            r = c.get(API, params={
                "action": "wbgetentities",
                "ids": "|".join(batch),
                "props": "claims",
                "format": "json",
            })
            r.raise_for_status()
            for qid, ent in r.json().get("entities", {}).items():
                claims = ent.get("claims", {})
                out[qid] = WikidataChem(
                    qid=qid,
                    cas_numbers=_string_claims(claims, P_CAS),
                    e_numbers=_string_claims(claims, P_ENUM),
                )
    return out
