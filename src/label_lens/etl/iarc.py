"""IARC monograph classifications loader. [SCAFFOLD]

Purpose: hydrate IARC hazard rows (group_1 | group_2a | group_2b | group_3),
CAS-keyed. IARC is a HAZARD assessment, not a legal status: rows land in
regulatory_status under jurisdiction='IARC' but must always be presented as
"cancer-hazard classification", never as a ban. Coverage is thin (only some
additives are classified), which is expected.

Source: 'List of Classifications by cancer site / by agent', downloadable
        spreadsheet keyed by agent name, group, and CAS.
        https://monographs.iarc.who.int/list-of-classifications
Transform: join on CAS; normalise the group label; capture exposure route
        (e.g. TiO2 2B is inhalation, not diet) into detail.
"""
from __future__ import annotations

SOURCE_URL = "https://monographs.iarc.who.int/list-of-classifications"


def load(slice_cas: set[str]) -> list[dict]:
    raise NotImplementedError("IARC bulk loader: Day-1 continuation. See module docstring.")
