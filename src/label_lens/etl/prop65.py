"""California OEHHA Prop 65 + AB 418 loader. [SCAFFOLD]

Purpose: hydrate US_CA regulatory_status rows. Two inputs:
  1. Prop 65 list (CAS-keyed) -> status='listed' with the listing basis
     (cancer / developmental / reproductive) in detail.
  2. AB 418 'California Food Safety Act' -> status='banned' (effective 2027) for
     its four additives: Red 3 (E127), potassium bromate (E924), BVO (E443),
     propylparaben (E216). Hardcoded from the bill text (no dataset).

Source: OEHHA Prop 65 list (Excel) + AB 418 statute.
        https://oehha.ca.gov/proposition-65/proposition-65-list
Transform: join Prop 65 on CAS; AB 418 is a fixed 4-row constant.
"""
from __future__ import annotations

SOURCE_URL = "https://oehha.ca.gov/media/downloads/proposition-65/p65single.xlsx"

# AB 418 bans these four from food effective 2027-01-01 (hardcoded from statute).
AB418_BANNED = ("E127", "E924", "E443", "E216")


def load(slice_cas: set[str]) -> list[dict]:
    raise NotImplementedError("Prop 65 bulk loader: Day-1 continuation. See module docstring.")
