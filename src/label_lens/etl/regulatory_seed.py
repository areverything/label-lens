"""Hand-curated, primary-source-cited regulatory status for the marquee slice.

This is intentionally NOT the full status matrix. It seeds the well-documented
divergences that drive the demo and the eval questions, each with a citation, so
the store lane is queryable on Day 1 and this doubles as the Day-2 gold set.
The bulk ETL loaders (fda/eu/iarc/prop65) will hydrate and reconcile the rest;
where they disagree with a curated-primary row, the curated row wins until a
human re-verifies.

Rows are keyed by E-number and mapped to CAS at load time. Fields:
  (e_number, jurisdiction, status, detail, citation, as_of)
"""
from __future__ import annotations

SEED: tuple[tuple[str, str, str, str, str, str], ...] = (
    # Titanium dioxide E171 -- the headline "same evidence, different call"
    ("E171", "EU", "banned", "Banned as a food additive; no longer considered safe (EFSA 2021 could not exclude genotoxicity).", "Commission Reg (EU) 2022/63", "2022-01-14"),
    ("E171", "US_FDA", "permitted", "Permitted for use as a color additive, <=1% by weight.", "21 CFR 73.575", "2024-01-01"),
    ("E171", "IARC", "not_classified", "No dietary carcinogenicity classification; IARC 2B relates to inhaled TiO2 dust, not food.", "IARC Monograph Vol. 93", "2010-01-01"),

    # Erythrosine / FD&C Red 3 E127 -- the recent FDA reversal
    ("E127", "US_FDA", "revoked", "FDA revoked authorization for use of FD&C Red No. 3 in food and ingested drugs.", "Fed. Register 90 FR 4636 (Jan 16 2025)", "2025-01-16"),
    ("E127", "EU", "authorised", "Authorised food colour under Annex II conditions.", "Reg (EC) 1333/2008 Annex II", "2024-01-01"),
    ("E127", "US_CA", "banned", "Banned from food effective 2027 under the California Food Safety Act.", "California AB 418 (2023)", "2027-01-01"),

    # Southampton dyes -- EU warning label vs FDA permitted
    ("E102", "EU", "authorised_warning", "Authorised but requires 'may have an adverse effect on activity and attention in children' label.", "Reg (EC) 1333/2008 Annex V", "2024-01-01"),
    ("E102", "US_FDA", "permitted", "Listed color additive (FD&C Yellow No. 5), certification required.", "21 CFR 74.705", "2024-01-01"),
    ("E110", "EU", "authorised_warning", "Southampton dye; requires child-attention warning label.", "Reg (EC) 1333/2008 Annex V", "2024-01-01"),
    ("E110", "US_FDA", "permitted", "Listed color additive (FD&C Yellow No. 6).", "21 CFR 74.706", "2024-01-01"),
    ("E129", "EU", "authorised_warning", "Southampton dye; requires child-attention warning label.", "Reg (EC) 1333/2008 Annex V", "2024-01-01"),
    ("E129", "US_FDA", "permitted", "Listed color additive (FD&C Red No. 40).", "21 CFR 74.340", "2024-01-01"),

    # Colours EU-authorised but not FDA-approved for food
    ("E104", "US_FDA", "not_approved", "Not an approved color additive for food in the US.", "21 CFR 74 (absent)", "2024-01-01"),
    ("E122", "US_FDA", "not_approved", "Not an approved color additive for food in the US.", "21 CFR 74 (absent)", "2024-01-01"),
    ("E124", "US_FDA", "not_approved", "Not an approved color additive for food in the US.", "21 CFR 74 (absent)", "2024-01-01"),
    ("E131", "US_FDA", "not_approved", "Not an approved color additive for food in the US.", "21 CFR 74 (absent)", "2024-01-01"),

    # Aspartame -- hazard-not-law flagship
    ("E951", "IARC", "group_2b", "Classified 'possibly carcinogenic to humans' (Group 2B); JECFA retained ADI 40 mg/kg bw.", "IARC/JECFA joint statement (Jul 2023)", "2023-07-14"),
    ("E951", "EU", "authorised", "Authorised sweetener; ADI 40 mg/kg bw/day.", "Reg (EC) 1333/2008 Annex II", "2024-01-01"),
    ("E951", "US_FDA", "permitted", "Approved general-purpose sweetener.", "21 CFR 172.804", "2024-01-01"),

    # BHA -- hazard + California
    ("E320", "IARC", "group_2b", "Butylated hydroxyanisole classified 'possibly carcinogenic to humans' (Group 2B).", "IARC Monograph Vol. 40", "1986-01-01"),
    ("E320", "US_CA", "listed", "Listed under Proposition 65 as a carcinogen.", "OEHHA Prop 65 list (BHA)", "1990-01-01"),

    # Cyclamate -- FDA ban vs EU authorised
    ("E952", "US_FDA", "banned", "General food use banned; delisting never reversed.", "34 FR 17063 (1969)", "1969-10-01"),
    ("E952", "EU", "authorised", "Authorised sweetener with use-level limits.", "Reg (EC) 1333/2008 Annex II", "2024-01-01"),

    # California AB 418 non-colour trio
    ("E216", "US_CA", "banned", "Propylparaben banned from food effective 2027.", "California AB 418 (2023)", "2027-01-01"),
    ("E216", "EU", "not_authorised", "Food additive authorisation withdrawn in 2006.", "Reg (EC) 1333/2008 (not listed)", "2006-01-01"),
    ("E443", "US_CA", "banned", "Brominated vegetable oil banned from food effective 2027.", "California AB 418 (2023)", "2027-01-01"),
    ("E443", "US_FDA", "revoked", "FDA revoked the authorization for BVO in food.", "89 FR 63765 (Aug 2024)", "2024-08-02"),
    ("E443", "EU", "not_authorised", "Not an authorised food additive in the EU.", "Reg (EC) 1333/2008 (not listed)", "2024-01-01"),
    ("E924", "US_CA", "banned", "Potassium bromate banned from food effective 2027.", "California AB 418 (2023)", "2027-01-01"),
    ("E924", "IARC", "group_2b", "Potassium bromate classified 'possibly carcinogenic to humans' (Group 2B).", "IARC Monograph Vol. 73", "1999-01-01"),
    ("E924", "US_FDA", "permitted", "Permitted as a flour treatment agent (with limits); FDA has urged voluntary discontinuation.", "21 CFR 136 / 137", "2024-01-01"),
    ("E924", "EU", "not_authorised", "Not authorised as a food additive in the EU/UK.", "Reg (EC) 1333/2008 (not listed)", "2024-01-01"),
)
