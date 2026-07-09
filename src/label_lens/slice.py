"""The v1 additive slice: colors-led + marquee hazards (~28 additives).

Deliberately small so the whole E-number -> CAS cross-walk is hand-verifiable.
Each entry is keyed by E-number and carries the family and the *regulatory hook*
(why it earns a place in the slice). CAS is NOT hardcoded here: it is resolved by
the pipeline (OFF taxonomy QID -> Wikidata P231) and cross-checked, so this file
stays a statement of scope, not a claim about chemistry.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SliceEntry:
    e_number: str          # canonical "E###" form
    name: str              # common English name
    family: str            # colour | preservative | antioxidant | sweetener | flour_treatment | emulsifier
    hook: str              # the regulatory-divergence reason it's in scope


SLICE: tuple[SliceEntry, ...] = (
    # --- Synthetic colours: the sharpest EU vs FDA vs California divergence ---
    SliceEntry("E102", "Tartrazine (FD&C Yellow 5)", "colour", "EU warning-label required (Southampton dyes); FDA permitted"),
    SliceEntry("E104", "Quinoline Yellow", "colour", "EU authorised w/ warning label; NOT FDA-approved for food"),
    SliceEntry("E110", "Sunset Yellow FCF (FD&C Yellow 6)", "colour", "Southampton dye; EU warning label; FDA permitted"),
    SliceEntry("E122", "Azorubine / Carmoisine", "colour", "EU authorised; NOT FDA-approved for food"),
    SliceEntry("E124", "Ponceau 4R", "colour", "EU authorised w/ warning label; NOT FDA-approved for food"),
    SliceEntry("E127", "Erythrosine (FD&C Red 3)", "colour", "FDA revoked food use Jan 2025 (Fed. Register); EU still authorised"),
    SliceEntry("E129", "Allura Red AC (FD&C Red 40)", "colour", "Southampton dye; EU warning label; FDA permitted"),
    SliceEntry("E131", "Patent Blue V", "colour", "EU authorised; NOT FDA-approved for food"),
    SliceEntry("E132", "Indigotine (FD&C Blue 2)", "colour", "authorised both EU and FDA; a low-divergence control"),
    SliceEntry("E133", "Brilliant Blue FCF (FD&C Blue 1)", "colour", "authorised both EU and FDA; a low-divergence control"),
    SliceEntry("E171", "Titanium dioxide", "colour", "EU banned in food 2022 (Reg 2022/63); FDA still permits (21 CFR 73.575)"),

    # --- Preservatives ---
    SliceEntry("E210", "Benzoic acid", "preservative", "reranking pair vs E211; benzene-formation concern w/ ascorbic acid"),
    SliceEntry("E211", "Sodium benzoate", "preservative", "reranking pair vs E210; widely used, EU + FDA authorised"),
    SliceEntry("E220", "Sulfur dioxide", "preservative", "mandatory allergen-style labelling; ADI story"),
    SliceEntry("E249", "Potassium nitrite", "preservative", "nitrite/nitrate cured-meat hazard; IARC processed-meat context"),
    SliceEntry("E250", "Sodium nitrite", "preservative", "nitrite/nitrate cured-meat hazard; IARC processed-meat context"),
    SliceEntry("E251", "Sodium nitrate", "preservative", "nitrite/nitrate cured-meat hazard"),
    SliceEntry("E252", "Potassium nitrate", "preservative", "nitrite/nitrate cured-meat hazard"),

    # --- Antioxidants ---
    SliceEntry("E320", "Butylated hydroxyanisole (BHA)", "antioxidant", "IARC Group 2B; California Prop 65 listed"),
    SliceEntry("E321", "Butylated hydroxytoluene (BHT)", "antioxidant", "contested evidence; EU + FDA authorised"),

    # --- Sweeteners ---
    SliceEntry("E950", "Acesulfame potassium", "sweetener", "EU + FDA authorised; ADI story"),
    SliceEntry("E951", "Aspartame", "sweetener", "IARC Group 2B (2023); the headline hazard-not-law case"),
    SliceEntry("E952", "Cyclamates", "sweetener", "EU authorised; FDA banned 1969 (still delisted)"),
    SliceEntry("E954", "Saccharin", "sweetener", "delisted from CA Prop 65; historical FDA warning removed"),
    SliceEntry("E955", "Sucralose", "sweetener", "EU + FDA authorised; recent genotoxicity debate"),

    # --- California AB 418 non-colour members (banned in CA from 2027) ---
    SliceEntry("E216", "Propylparaben", "preservative", "CA AB 418 banned; EU withdrew food authorisation 2006"),
    SliceEntry("E443", "Brominated vegetable oil (BVO)", "emulsifier", "CA AB 418 + FDA revoked 2024; never EU-authorised"),
    SliceEntry("E924", "Potassium bromate", "flour_treatment", "CA AB 418 banned; IARC Group 2B; not EU/UK authorised; FDA permits"),
)

BY_E_NUMBER: dict[str, SliceEntry] = {e.e_number: e for e in SLICE}


def e_num_digits(e_number: str) -> str:
    """'E171' -> '171' to match the OFF taxonomy's bare e_number field."""
    return e_number.lstrip("Ee").strip()
