# Label Lens

A food-additive **intelligence** RAG app. Scan a product and ask what a scanner can't answer: which additives are **banned somewhere else**, what the **evidence** actually says, and whether you're **over a safe limit across your day**. Cited from Open Food Facts, four regulators, and distilled per-additive briefs. AIEC capstone; the full build plan is in [`PLAN.md`](./PLAN.md).

## Quick Start

```bash
cd ~/code/courses/label_lens
uv sync                                   # install deps (Python 3.13 via uv)
uv run python scripts/build_spine.py      # build the canonical additive store -> data/label_lens.duckdb
```

That resolves the 28-additive slice's **E-number → CAS** spine (OFF taxonomy + Wikidata), loads the canonical `additives` table and the curated `regulatory_status` seed into DuckDB, and prints a resolution + coverage report. Query it:

```bash
uv run python - <<'PY'
from label_lens.db import connect
con = connect()
for row in con.execute(
    "SELECT r.jurisdiction, r.status, r.citation FROM additives a "
    "JOIN regulatory_status r USING(cas) WHERE a.e_number='E171'").fetchall():
    print(row)   # E171: EU banned / US_FDA permitted / IARC not_classified
PY
```

No API keys needed for Day 1. The LLM gateway key (for Day 2+) goes in `.env.local`.

## What's built (Day 1: spine + join)

- **The CAS spine.** `E-number → name/QID` from the OFF additives taxonomy, `QID → CAS` via Wikidata property P231. 28/28 additives resolve to a canonical CAS; two hand-resolved overrides (E127 salt form, E443 mixture) are documented in `etl/spine.py`.
  - Key finding: **the OFF taxonomy does not carry CAS** (the plan assumed it did). Wikidata P231 is the bridge instead.
- **The canonical store** (`data/label_lens.duckdb`): `additives` (keyed by CAS), `regulatory_status` (one row per additive × jurisdiction, EU / US_FDA / US_CA / IARC), and an empty `product` table awaiting the OFF load.
- **Curated regulatory seed** (`etl/regulatory_seed.py`): ~32 primary-source-cited status rows for the marquee divergences (E171, E127, aspartame IARC-2B, the AB 418 four, ...). Hand-verified, so it doubles as the Day-2 gold set.
- **Legal status is kept separate from hazard.** IARC rows are cancer-*hazard* classifications, never bans. Baked into the schema, not bolted on.

## Layout

```
src/label_lens/
  slice.py              # the 28-additive v1 slice (scope, not chemistry)
  config.py  db.py  schema.sql
  etl/
    off_taxonomy.py     # E-number -> name/class/QID/EFSA        [live]
    wikidata.py         # QID -> CAS (P231) + E-number (P628)    [live]
    spine.py            # the join + CAS overrides + warnings    [live]
    regulatory_seed.py  # curated cited status rows              [live]
    fda.py eu.py iarc.py prop65.py off_products.py               [scaffold, Day-1 continuation]
scripts/build_spine.py  # Day-1 entrypoint
```

## Roadmap

Day 1 spine ✅ · bulk regulator loaders (hydrate the full status matrix) · OFF product load (US candy) · Day 2 distilled briefs + gold verify · Day 3 LangGraph agent + retrieval + UI · Day 4 retrieval-ladder eval · Day 5 ablation + write-up. Full detail in [`PLAN.md`](./PLAN.md).
