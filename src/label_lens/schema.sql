-- Label Lens canonical store. CAS is the join key across every regulator.
-- Legal status (regulatory_status) is kept strictly separate from hazard
-- assessment (hazard) so "banned somewhere" is never conflated with "harmful".

CREATE TABLE IF NOT EXISTS additives (
    cas                 TEXT PRIMARY KEY,   -- canonical CAS Registry Number
    e_number            TEXT,               -- canonical "E###"
    name                TEXT,
    family              TEXT,               -- colour | preservative | antioxidant | sweetener | ...
    additives_classes   TEXT,              -- comma-joined OFF classes
    colour_index        TEXT,               -- CI number for dyes, else NULL
    wikidata_qid        TEXT,
    efsa_evaluation_url TEXT,
    efsa_adi            TEXT,               -- structured ADI string from OFF taxonomy, if any
    hook                TEXT,               -- why it's in the slice (regulatory hook)
    cas_alternates      TEXT,               -- comma-joined alternate CAS forms (hydrates/salts)
    resolution_status   TEXT                -- ok | ambiguous_cas | no_cas | not_in_taxonomy
);

-- One row per additive x jurisdiction. status is the legal fact; detail + citation
-- carry provenance. source distinguishes hand-curated primary-source rows from
-- rows hydrated by the bulk ETL loaders.
CREATE TABLE IF NOT EXISTS regulatory_status (
    cas          TEXT NOT NULL,
    jurisdiction TEXT NOT NULL,             -- EU | US_FDA | US_CA | IARC
    status       TEXT,                      -- e.g. authorised | banned | permitted | revoked | listed | group_2b
    detail       TEXT,
    citation     TEXT,
    source       TEXT,                      -- curated-primary | fda-bulk | eu-bulk | iarc-bulk | prop65-bulk
    as_of        TEXT,
    PRIMARY KEY (cas, jurisdiction, status)
);

-- Product facts for the chosen category (US candy/confectionery), loaded from
-- the OFF Parquet via DuckDB. Empty until the product ETL runs.
CREATE TABLE IF NOT EXISTS product (
    barcode          TEXT PRIMARY KEY,
    name             TEXT,
    brands           TEXT,
    categories       TEXT,
    countries        TEXT,
    additives_tags   TEXT,                  -- comma-joined en:e### tags
    ingredients_text TEXT,
    off_url          TEXT
);
