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

    # Blues both regulators authorise -- the "they agree here" control alongside the Southampton dyes
    ("E132", "EU", "authorised", "Authorised food colour under Annex II conditions; no child-attention warning required.", "Reg (EC) 1333/2008 Annex II", "2024-01-01"),
    ("E132", "US_FDA", "permitted", "Listed color additive (FD&C Blue No. 2), certification required.", "21 CFR 74.102", "2024-01-01"),
    ("E133", "EU", "authorised", "Authorised food colour under Annex II conditions; no child-attention warning required.", "Reg (EC) 1333/2008 Annex II", "2024-01-01"),
    ("E133", "US_FDA", "permitted", "Listed color additive (FD&C Blue No. 1), certification required.", "21 CFR 74.101", "2024-01-01"),

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

    # Remaining in-scope additives, so no candy ingredient in scope returns a
    # blank status. EU rows sit in the Union list (Reg 1333/2008 Annex II); US
    # CFR sections verified against eCFR / Cornell LII; IARC groups from the
    # named monographs. Note the nitrite/nitrate CFR mapping is counter-intuitive
    # (172.160 is potassium NITRATE; potassium nitrite is prior-sanctioned only).

    # Benzoate preservatives -- both regulators allow; the E210/E211 near-duplicate pair
    ("E210", "EU", "authorised", "Authorised preservative in the Union list, subject to Annex II conditions of use.", "Reg (EC) 1333/2008 Annex II", "2024-01-01"),
    ("E210", "US_FDA", "permitted", "GRAS antimicrobial preservative, use not exceeding 0.1 percent.", "21 CFR 184.1021", "2024-01-01"),
    ("E211", "EU", "authorised", "Authorised preservative in the Union list, subject to Annex II conditions of use.", "Reg (EC) 1333/2008 Annex II", "2024-01-01"),
    ("E211", "US_FDA", "permitted", "GRAS antimicrobial preservative, use not exceeding 0.1 percent.", "21 CFR 184.1733", "2024-01-01"),

    # Sulfur dioxide -- allowed both sides, but each imposes a different restriction
    ("E220", "EU", "authorised", "Authorised sulphite preservative; foods above 10 mg/kg must be labelled 'contains sulphites'.", "Reg (EC) 1333/2008 Annex II", "2024-01-01"),
    ("E220", "US_FDA", "permitted", "GRAS, but not permitted on meats, on recognised vitamin B1 sources, or on raw fruit and vegetables sold as fresh.", "21 CFR 182.3862", "2024-01-01"),

    # Nitrites / nitrates -- EU cut the limits in 2023; IARC 2A is for the endogenous-nitrosation exposure, not the compound
    ("E249", "EU", "authorised", "Authorised preservative; maximum added amounts lowered by Reg (EU) 2023/2108, reduced levels applying from Oct 2025.", "Reg (EC) 1333/2008 Annex II (amended by Reg (EU) 2023/2108)", "2023-01-01"),
    ("E249", "US_FDA", "permitted", "Prior-sanctioned colour fixative and preservative in the curing of red meat and poultry.", "21 CFR 181.34", "2024-01-01"),
    ("E249", "IARC", "group_2a", "Ingested nitrate or nitrite 'under conditions that result in endogenous nitrosation' is probably carcinogenic; the rating is for that exposure condition, not the additive itself.", "IARC Monograph Vol. 94", "2010-01-01"),
    ("E250", "EU", "authorised", "Authorised preservative; maximum added amounts lowered by Reg (EU) 2023/2108, reduced levels applying from Oct 2025.", "Reg (EC) 1333/2008 Annex II (amended by Reg (EU) 2023/2108)", "2023-01-01"),
    ("E250", "US_FDA", "permitted", "Permitted preservative and colour fixative in cured and smoked meat and fish, with set limits.", "21 CFR 172.175", "2024-01-01"),
    ("E250", "IARC", "group_2a", "Ingested nitrate or nitrite 'under conditions that result in endogenous nitrosation' is probably carcinogenic; the rating is for that exposure condition, not the additive itself.", "IARC Monograph Vol. 94", "2010-01-01"),
    ("E251", "EU", "authorised", "Authorised preservative; maximum added amounts lowered by Reg (EU) 2023/2108, reduced levels applying from Oct 2025.", "Reg (EC) 1333/2008 Annex II (amended by Reg (EU) 2023/2108)", "2023-01-01"),
    ("E251", "US_FDA", "permitted", "Permitted preservative and colour fixative in cured fish and meat-curing preparations, up to 500 ppm.", "21 CFR 172.170", "2024-01-01"),
    ("E251", "IARC", "group_2a", "Ingested nitrate or nitrite 'under conditions that result in endogenous nitrosation' is probably carcinogenic; the rating is for that exposure condition, not the additive itself.", "IARC Monograph Vol. 94", "2010-01-01"),
    ("E252", "EU", "authorised", "Authorised preservative; maximum added amounts lowered by Reg (EU) 2023/2108, reduced levels applying from Oct 2025.", "Reg (EC) 1333/2008 Annex II (amended by Reg (EU) 2023/2108)", "2023-01-01"),
    ("E252", "US_FDA", "permitted", "Permitted curing agent in cod roe, up to 200 ppm in the finished roe.", "21 CFR 172.160", "2024-01-01"),
    ("E252", "IARC", "group_2a", "Ingested nitrate or nitrite 'under conditions that result in endogenous nitrosation' is probably carcinogenic; the rating is for that exposure condition, not the additive itself.", "IARC Monograph Vol. 94", "2010-01-01"),

    # BHT -- IARC Group 3, the deliberate contrast to BHA (Group 2B) above
    ("E321", "EU", "authorised", "Authorised antioxidant in the Union list, subject to Annex II conditions of use.", "Reg (EC) 1333/2008 Annex II", "2024-01-01"),
    ("E321", "US_FDA", "permitted", "GRAS antioxidant, up to 0.02 percent of the fat or oil content.", "21 CFR 182.3173", "2024-01-01"),
    ("E321", "IARC", "group_3", "Not classifiable as to carcinogenicity to humans (unlike BHA, which is Group 2B).", "IARC Monograph Vol. 40", "1986-01-01"),

    # Sweeteners -- acesulfame K and sucralose (both allowed); saccharin, whose IARC 2B was withdrawn in 1999
    ("E950", "EU", "authorised", "Authorised sweetener in the Union list, subject to Annex II conditions of use.", "Reg (EC) 1333/2008 Annex II", "2024-01-01"),
    ("E950", "US_FDA", "permitted", "Approved as a general-purpose sweetener and flavour enhancer in foods, except in meat and poultry.", "21 CFR 172.800", "2024-01-01"),
    ("E954", "EU", "authorised", "Authorised sweetener (saccharin and its salts) in the Union list, subject to Annex II conditions.", "Reg (EC) 1333/2008 Annex II", "2024-01-01"),
    ("E954", "US_FDA", "permitted", "Permitted sweetening agent (saccharin and its ammonium, calcium and sodium salts); the 1970s warning-label requirement was repealed in 2000.", "21 CFR 180.37", "2024-01-01"),
    ("E954", "IARC", "group_3", "Not classifiable as to carcinogenicity to humans; downgraded from Group 2B in 1999 as the rat-bladder mechanism was found not relevant to humans.", "IARC Monograph Vol. 73", "1999-01-01"),
    ("E955", "EU", "authorised", "Authorised sweetener in the Union list, subject to Annex II conditions of use.", "Reg (EC) 1333/2008 Annex II", "2024-01-01"),
    ("E955", "US_FDA", "permitted", "Approved as a sweetener in foods generally, under good manufacturing practice.", "21 CFR 172.831", "2024-01-01"),
)
