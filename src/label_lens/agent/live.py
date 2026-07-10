"""Live lane: two US-government APIs called at question time.

These keep answers current with regulator actions the static briefs cannot
pre-bake: product recalls (openFDA food-enforcement) and new rules such as bans
or authorization revocations (Federal Register). Both are read-only public APIs,
no key required. Network failures degrade to an empty, explained result rather
than raising, so one flaky endpoint never sinks an answer.
"""
from __future__ import annotations

import httpx

from label_lens.config import USER_AGENT

OPENFDA_URL = "https://api.fda.gov/food/enforcement.json"
FEDREG_URL = "https://www.federalregister.gov/api/v1/documents.json"
_TIMEOUT = 20


def openfda_recalls(term: str, limit: int = 5) -> dict:
    """Recent food recalls mentioning `term` (a product, brand, or additive).

    Searches the recall reason first, then the product description. openFDA
    answers 404 when nothing matches, which we report as zero recalls.
    """
    for field in ("reason_for_recall", "product_description"):
        try:
            r = httpx.get(
                OPENFDA_URL,
                params={"search": f'{field}:"{term}"', "limit": limit},
                headers={"User-Agent": USER_AGENT},
                timeout=_TIMEOUT,
            )
        except httpx.HTTPError as e:
            return {"term": term, "error": f"openFDA unreachable: {e}", "recalls": []}
        if r.status_code == 404:
            continue  # no matches on this field; try the next
        if r.status_code != 200:
            return {"term": term, "error": f"openFDA HTTP {r.status_code}", "recalls": []}
        results = r.json().get("results", [])
        if results:
            return {"term": term, "recalls": [
                {
                    "product": x.get("product_description", "")[:200],
                    "reason": x.get("reason_for_recall", "")[:200],
                    "status": x.get("status", ""),
                    "classification": x.get("classification", ""),
                    "recall_date": x.get("recall_initiation_date", ""),
                    "recalling_firm": x.get("recalling_firm", ""),
                }
                for x in results
            ]}
    return {"term": term, "recalls": []}  # searched both fields, nothing found


def federal_register(term: str, limit: int = 5) -> dict:
    """Recent Federal Register documents mentioning `term`, newest first.

    Surfaces new bans and authorization revocations (e.g. the 2025 FD&C Red 3
    revocation) that post-date the briefs.
    """
    try:
        r = httpx.get(
            FEDREG_URL,
            params={
                "conditions[term]": term,
                # Scope to the FDA and rank by relevance: the term search is broad
                # full-text, so unscoped "newest" buries the real rule under noise.
                "conditions[agencies][]": "food-and-drug-administration",
                "per_page": limit,
                "order": "relevance",
                "fields[]": ["title", "publication_date", "html_url", "type",
                             "abstract", "document_number"],
            },
            headers={"User-Agent": USER_AGENT},
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
    except httpx.HTTPError as e:
        return {"term": term, "error": f"Federal Register unreachable: {e}", "documents": []}
    results = r.json().get("results", [])
    return {"term": term, "documents": [
        {
            "title": x.get("title", ""),
            "type": x.get("type", ""),
            "published": x.get("publication_date", ""),
            "abstract": (x.get("abstract") or "")[:300],
            "url": x.get("html_url", ""),
        }
        for x in results
    ]}
