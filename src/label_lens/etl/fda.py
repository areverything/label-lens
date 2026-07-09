"""FDA 'Substances Added to Food' (SAF/GRAS) bulk loader. [SCAFFOLD]

Purpose: hydrate US_FDA regulatory_status rows and cross-check CAS. The FDA
inventory is CAS-keyed, so it both confirms the spine's CAS and supplies the
21 CFR citation + GRAS/permitted status per additive.

Source: FDA CFSAN 'Substances Added to Food' inventory (downloadable Excel).
        https://www.cfsanappsexternal.fda.gov/scripts/fdcc/?set=FoodSubstances
Transform: filter to the slice CAS set, map FDA status -> our status vocabulary
        (permitted | revoked | not_approved | gras), attach 21 CFR cite.
Reconciliation: where this disagrees with a curated-primary seed row, keep the
        curated row and emit a diff for human review (curated wins until verified).
"""
from __future__ import annotations

SOURCE_URL = "https://www.cfsanappsexternal.fda.gov/scripts/fdcc/?set=FoodSubstances"


def load(slice_cas: set[str]) -> list[dict]:
    raise NotImplementedError("FDA bulk loader: Day-1 continuation. See module docstring.")
