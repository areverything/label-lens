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
    -- Product front images live in data/product_images.json (barcode -> URL), not
    -- here: the committed DB is mutated at runtime, so a new binary column may not
    -- survive a redeploy; a committed text sidecar always does.
);

-- User memory: one diet/allergy profile row per user, plus an append-only log of
-- products they asked about. Powers cumulative, personalised questions. Also
-- created on demand by agent/memory.py so an existing store gains them in place.
CREATE TABLE IF NOT EXISTS user_profile (
    user_id    TEXT PRIMARY KEY,
    diet       TEXT,
    allergies  TEXT,
    updated_at TEXT
);
CREATE SEQUENCE IF NOT EXISTS product_log_seq START 1;
CREATE TABLE IF NOT EXISTS product_log (
    id        BIGINT DEFAULT nextval('product_log_seq') PRIMARY KEY,
    user_id   TEXT NOT NULL,
    barcode   TEXT,
    name      TEXT,
    logged_at TEXT
);
