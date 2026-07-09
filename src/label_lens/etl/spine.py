"""Build the E-number <-> CAS spine for the slice.

Flow per additive:
  slice E-number -> OFF taxonomy entry -> Wikidata QID -> CAS (P231)
with a cross-check that the E-number Wikidata claims (P628) matches the one the
taxonomy and the slice claim. Emits one AdditiveRecord per slice entry plus a
resolution status and human-readable warnings for anything that needs a look.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from label_lens.etl import off_taxonomy, wikidata
from label_lens.slice import SLICE, e_num_digits


@dataclass
class AdditiveRecord:
    cas: str | None
    e_number: str
    name: str
    family: str
    additives_classes: str
    colour_index: str | None
    wikidata_qid: str | None
    efsa_evaluation_url: str | None
    efsa_adi: str | None
    hook: str
    cas_alternates: str
    resolution_status: str            # ok | ambiguous_cas | no_cas | no_qid | not_in_taxonomy
    warnings: list[str] = field(default_factory=list)


# Hand-resolved CAS where the automated bridge is wrong or missing. Each entry is
# (canonical_cas, note, verified). "verified" means confirmed against a second
# source (Wikidata P231); False means curated and awaiting bulk reconciliation.
CAS_OVERRIDES: dict[str, tuple[str, str, bool]] = {
    # Wikidata's erythrosine QID gives the acid (15905-32-5); FDA/EU key FD&C Red 3
    # as the disodium salt. Confirmed via Wikidata Q27888290 "erythrosine sodium".
    "E127": ("16423-68-0", "prefer FD&C Red 3 disodium salt over acid form for the FDA join", True),
    # BVO is a mixture; its QID carries no P231 and no single-compound CAS exists in
    # Wikidata. Curated from FDA/EU nomenclature, flag for FDA-bulk reconciliation.
    "E443": ("8016-94-9", "BVO mixture CAS, absent from Wikidata; verify against FDA bulk", False),
}


def _norm_enum(s: str) -> str:
    """'E102' / 'e 102' / '102' -> '102' for comparison."""
    return s.upper().replace("E", "").replace(" ", "").strip()


def build_spine() -> list[AdditiveRecord]:
    tax = off_taxonomy.load()

    # First pass: map each slice entry to its OFF taxonomy entry + QID.
    qids: list[str] = []
    for entry in SLICE:
        off = tax.get(e_num_digits(entry.e_number))
        if off and off.wikidata_qid:
            qids.append(off.wikidata_qid)
    wd = wikidata.fetch(qids)

    records: list[AdditiveRecord] = []
    for entry in SLICE:
        digits = e_num_digits(entry.e_number)
        off = tax.get(digits)
        warnings: list[str] = []

        if off is None:
            records.append(AdditiveRecord(
                cas=None, e_number=entry.e_number, name=entry.name, family=entry.family,
                additives_classes="", colour_index=None, wikidata_qid=None,
                efsa_evaluation_url=None, efsa_adi=None, hook=entry.hook,
                cas_alternates="", resolution_status="not_in_taxonomy",
                warnings=["E-number absent from OFF additives taxonomy"],
            ))
            continue

        qid = off.wikidata_qid
        chem = wd.get(qid) if qid else None
        cas_list = list(chem.cas_numbers) if chem else []

        # Apply a hand-resolved override: promote it to canonical, demote the
        # Wikidata-derived CAS to alternates.
        override = CAS_OVERRIDES.get(entry.e_number)
        if override:
            ov_cas, ov_note, ov_verified = override
            cas_list = [ov_cas] + [c for c in cas_list if c != ov_cas]
            warnings.append(f"CAS override ({'verified' if ov_verified else 'curated'}): {ov_note}")

        if qid is None:
            status = "no_qid"
            warnings.append("OFF taxonomy entry has no Wikidata QID; CAS unresolved")
        elif not cas_list:
            status = "no_cas"
            warnings.append(f"Wikidata {qid} carries no CAS (P231)")
        elif len(cas_list) > 1:
            status = "ambiguous_cas"
            warnings.append(f"Wikidata {qid} lists {len(cas_list)} CAS numbers; took first as canonical")
        else:
            status = "ok"

        # Cross-check the E-number Wikidata claims against the slice.
        if chem and chem.e_numbers:
            wd_enums = {_norm_enum(x) for x in chem.e_numbers}
            if _norm_enum(entry.e_number) not in wd_enums:
                warnings.append(
                    f"E-number mismatch: slice={entry.e_number} vs Wikidata P628={chem.e_numbers}"
                )

        records.append(AdditiveRecord(
            cas=cas_list[0] if cas_list else None,
            e_number=entry.e_number,
            name=entry.name,
            family=entry.family,
            additives_classes=",".join(off.additives_classes),
            colour_index=off.colour_index,
            wikidata_qid=qid,
            efsa_evaluation_url=off.efsa_evaluation_url,
            efsa_adi=off.efsa_adi,
            hook=entry.hook,
            cas_alternates=",".join(cas_list[1:]),
            resolution_status=status,
            warnings=warnings,
        ))
    return records
