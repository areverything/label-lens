# Label Lens

Scan a packaged food and understand its additives: which ones are **banned in other countries**, what the **scientific evidence** actually says, and whether you're **over a safe daily limit**. Every answer is cited from official regulators, not vibes. This is an AI Engineering Certification capstone; the detailed build plan lives in [`PLAN.md`](./PLAN.md).

## What are food additives?

Additives are substances mixed into packaged food for a purpose: **colors** (make candy bright), **preservatives** (stop it going bad), **sweeteners** (sugar-free soda), **antioxidants** (keep fats from turning rancid), and more. They're useful. Preservatives prevent food poisoning and waste; colors and sweeteners make food people actually want to eat, often more cheaply.

The catch is that some additives are also *contested*. A few colors have been linked to hyperactivity in children. A handful are flagged as possible carcinogens. And regulators around the world disagree sharply about which ones are safe: an additive that's normal in a US candy bar may be banned, or carry a warning label, in Europe.

That disagreement is the whole point of this app. **"Banned somewhere" is not the same as "proven harmful."** Often two regulators looked at the *same* evidence and made different judgment calls. Label Lens shows you what each regulator decided and what the evidence says, keeps those two things separate, and refuses to give medical advice.

## The hard part: nobody agrees on names

To answer "is this additive banned in the EU?" you have to combine data from several regulators. But each one identifies additives *differently*, and there is no ready-made table linking them:

- **Europe** uses **E-numbers**: a short code for each approved additive (E100s are colors, E200s preservatives, and so on). Titanium dioxide is `E171`.
- **The US FDA** uses chemical names and a different ID.
- **Cancer researchers (IARC)** use yet another naming scheme.

The one identifier they *can* share is the **CAS number**, a globally unique ID assigned to every chemical substance (titanium dioxide is `13463-67-7`). So the core engineering task is matching each additive across all these sources using CAS as the common key. This matching is the moat: no single database and no chatbot can just hand it to you.

## Quick Start

```bash
cd ~/code/courses/label_lens
uv sync                                   # install dependencies (Python 3.13 via uv)
uv run python scripts/build_spine.py      # build the additive database -> data/label_lens.duckdb
```

This builds a clean, deduplicated table of additives (each linked to its CAS number) plus their legal status in each region, and prints a coverage report. Then you can query it:

```bash
uv run python - <<'PY'
from label_lens.db import connect
con = connect()
for row in con.execute(
    "SELECT r.jurisdiction, r.status, r.citation FROM additives a "
    "JOIN regulatory_status r USING(cas) WHERE a.e_number='E171'").fetchall():
    print(row)
PY
# Titanium dioxide (E171): banned in the EU, permitted by the US FDA,
# and NOT a dietary cancer classification. Same chemical, three verdicts.
```

No API keys are needed to build the database. An LLM key (for the later question-answering features) goes in `.env.local`.

## How the database is built

The starting scope is deliberately small and hand-checkable: **28 additives** (mostly food colors, plus a few high-profile preservatives and sweeteners) found in **US candy**.

1. **Names and codes** come from [Open Food Facts](https://openfoodfacts.org) (OFF), a free, crowd-sourced database of the world's packaged foods. Its *additives taxonomy* is a structured list mapping each E-number to a name, a category, and a link to [Wikidata](https://www.wikidata.org).
2. **CAS numbers** are missing from Open Food Facts (a discovery: the plan assumed they were there). We get them from Wikidata instead, which stores the CAS number for each chemical. This is the crosswalk: `E-number → Wikidata → CAS`.
3. **Legal status** in each region (EU, US FDA, California, plus the IARC cancer classification) is currently a hand-curated, source-cited set covering the most important cases. It doubles as a verified answer key for testing.

Everything lands in a single [DuckDB](https://duckdb.org) file (a lightweight local database) with three tables: `additives` (one row per substance, keyed by CAS), `regulatory_status` (one row per additive per region), and `product` (the scanned foods, not yet loaded).

## Project layout

```
src/label_lens/
  slice.py              # the 28 additives we cover, and why each one is interesting
  config.py  db.py  schema.sql
  etl/
    off_taxonomy.py     # read Open Food Facts: E-number -> name, category, Wikidata id   [working]
    wikidata.py         # look up CAS numbers from Wikidata                                [working]
    spine.py            # match everything together into one table                        [working]
    regulatory_seed.py  # curated, cited legal-status rows                                 [working]
    fda.py eu.py iarc.py prop65.py off_products.py   # bulk data loaders                   [scaffolded, next]
scripts/build_spine.py  # builds the database
```

## Status and what's next

**Working now:** all 28 additives resolve to a CAS number; the database builds and answers regional-status questions with citations.

**Next:** load real US candy products from Open Food Facts, expand the legal-status data from the marquee cases to full coverage via the bulk loaders, then generate the per-additive evidence briefs that power the question-answering. See [`PLAN.md`](./PLAN.md) for the full picture.
