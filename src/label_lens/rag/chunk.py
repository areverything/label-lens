"""Split a per-additive brief into section chunks, one per labelled section.

Section-based chunking (identity / regulatory status / evidence), chosen so each
retrieved passage is self-contained and keeps its citation intact. See
TECH_DESIGN → Chunking. The title line carries the additive identity, which we
attach to every chunk as metadata so a retrieved passage always knows which
additive it belongs to.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# "# Tartrazine (FD&C Yellow 5) (E102, CAS 1934-21-0)" -> name, e_number, cas.
# The name may itself contain parentheses, so anchor on the final "(E..., CAS ...)".
_TITLE = re.compile(r"^#\s+(?P<name>.+?)\s+\((?P<e>E\d+),\s*CAS\s+(?P<cas>[\d-]+)\)\s*$")


@dataclass
class Chunk:
    chunk_id: str          # "E102::Evidence" -- stable, unique per section
    section: str           # "Identity" | "Regulatory status" | "Evidence"
    text: str              # the section heading + body, verbatim
    e_number: str
    cas: str
    name: str


def chunk_brief(text: str) -> list[Chunk]:
    lines = text.splitlines()
    m = _TITLE.match(lines[0]) if lines else None
    if not m:
        raise ValueError(f"brief has no parseable title line: {lines[:1]}")
    name, e_number, cas = m["name"], m["e"], m["cas"]

    chunks: list[Chunk] = []
    section: str | None = None
    body: list[str] = []

    def flush() -> None:
        if section is None:
            return
        chunks.append(Chunk(
            chunk_id=f"{e_number}::{section}",
            section=section,
            text=f"## {section}\n" + "\n".join(body).strip(),
            e_number=e_number, cas=cas, name=name,
        ))

    for line in lines[1:]:
        h = re.match(r"^##\s+(?P<title>.+?)\s*$", line)
        if h:
            flush()
            section = h["title"]
            body = []
        elif section is not None:
            body.append(line)
    flush()
    return chunks
