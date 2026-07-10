"""Render a per-additive brief: deterministic facts + a grounded LLM narrative.

The Identity and Regulatory-status sections are rendered straight from the store
(no LLM, so they cannot invent). The LLM writes only the Evidence narrative, and
is instructed to use ONLY the provided facts and to cite each claim, so the
distilled prose stays faithful. Briefs are written as one markdown file per
additive, split into the labelled sections the chunking strategy relies on.
"""
from __future__ import annotations

from pathlib import Path

import duckdb

from label_lens.briefs.assemble import Facts, JURISDICTION_LABEL, JURISDICTION_ORDER, assemble
from label_lens.config import DATA
from label_lens.db import connect
from label_lens import llm

BRIEFS_DIR = DATA / "briefs"

_SYSTEM = (
    "You write concise, strictly factual briefs about food additives for a consumer "
    "safety app. Use ONLY the facts provided by the user. Every factual claim must end "
    "with its citation in parentheses, taken from the facts. Never invent facts, numbers, "
    "or citations. Keep three things separate and never conflate them: a jurisdiction's "
    "LEGAL status (banned/permitted), a cancer-HAZARD classification (e.g. IARC group), "
    "and personal HARM. Do not give medical advice. If evidence is thin, say so plainly."
)


def _identity_md(f: Facts) -> str:
    lines = [
        "## Identity",
        f"- **Name:** {f.name}",
        f"- **E-number:** {f.e_number}",
        f"- **CAS:** {f.cas}" + (f" (also {f.cas_alternates})" if f.cas_alternates else ""),
        f"- **Family:** {f.family}",
    ]
    if f.colour_index:
        lines.append(f"- **Colour Index:** {f.colour_index}")
    return "\n".join(lines)


def _status_md(f: Facts) -> str:
    lines = ["## Regulatory status", "",
             "| Jurisdiction | Status | Detail | Citation |",
             "|---|---|---|---|"]
    present = {r["jurisdiction"] for r in f.status}
    for r in f.status:
        lines.append(
            f"| {JURISDICTION_LABEL.get(r['jurisdiction'], r['jurisdiction'])} "
            f"| {r['status']} | {r['detail']} | {r['citation']} |"
        )
    missing = [j for j in JURISDICTION_ORDER if j not in present]
    if missing:
        labels = ", ".join(JURISDICTION_LABEL[j] for j in missing)
        lines += ["", f"_No regulatory status compiled yet for: {labels}._"]
    return "\n".join(lines)


def _facts_block(f: Facts) -> str:
    """The facts handed to the LLM, each line carrying its own citation."""
    rows = [f"- {JURISDICTION_LABEL.get(r['jurisdiction'], r['jurisdiction'])}: "
            f"{r['status']} - {r['detail']} ({r['citation']})" for r in f.status]
    ev = []
    if f.efsa_adi:
        ev.append(f"- EFSA acceptable daily intake: {f.efsa_adi} (EFSA re-evaluation, {f.efsa_url or 'EFSA'})")
    if f.efsa_url and not f.efsa_adi:
        ev.append(f"- EFSA re-evaluation on record ({f.efsa_url})")
    return (f"Additive: {f.name} ({f.e_number}, CAS {f.cas}), family {f.family}.\n"
            "Regulatory status rows:\n" + ("\n".join(rows) or "- none on record") +
            "\nEvidence facts:\n" + ("\n".join(ev) or "- none on record"))


def _narrative(f: Facts, *, model: str | None = None) -> str:
    user = (
        _facts_block(f) + "\n\n"
        "Write two short paragraphs, citing each claim from the facts above:\n"
        "1. How regulators diverge on this additive and (if the facts say) why.\n"
        "2. What the safety evidence says (EFSA intake, IARC classification if any), "
        "making clear that 'banned somewhere' is not the same as 'proven harmful'."
    )
    return llm.chat([{"role": "system", "content": _SYSTEM},
                     {"role": "user", "content": user}], model=model)


def render_brief(f: Facts, narrative: str) -> str:
    return "\n\n".join([
        f"# {f.name} ({f.e_number}, CAS {f.cas})",
        _identity_md(f),
        _status_md(f),
        "## Evidence\n\n" + narrative,
    ]) + "\n"


def build_all(out_dir: Path = BRIEFS_DIR, *, model: str | None = None) -> int:
    """Generate a brief for every resolved additive. Requires the LLM gateway."""
    if not llm.is_configured():
        raise llm.LLMNotConfigured(
            "Set OPENROUTER_API_KEY in .env.local before building briefs."
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    con = connect()
    cas_list = [c for (c,) in con.execute(
        "SELECT cas FROM additives WHERE resolution_status != 'not_in_taxonomy' ORDER BY e_number"
    ).fetchall()]
    n = 0
    for cas in cas_list:
        f = assemble(con, cas)
        brief = render_brief(f, _narrative(f, model=model))
        (out_dir / f"{f.e_number}.md").write_text(brief)
        n += 1
    con.close()
    return n
