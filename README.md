# Label Lens

Scan a packaged food and understand its additives: which ones are **banned or restricted in other countries**, what the **scientific evidence** actually says, and whether any are under a recall or a fresh government ban. Every answer is cited from official regulators. This is an AI Engineering Certification capstone.

## What are food additives?

Additives are substances mixed into packaged food for a purpose: **colors** (make candy bright), **preservatives** (stop it spoiling), **sweeteners** (sugar-free soda), **antioxidants** (keep fats from going rancid). They're useful. Preservatives prevent food poisoning and waste; colors and sweeteners make food people want to eat, often more cheaply.

The catch is that some are *contested*. A few colors have been linked to hyperactivity in children; a handful are flagged as possible carcinogens; and regulators disagree sharply, so an additive that's normal in a US candy bar may be banned, or carry a warning label, in Europe. **"Banned somewhere" is not the same as "proven harmful"**: often two regulators looked at the same evidence and made different calls. Label Lens shows what each regulator decided and what the evidence says, keeps those two things separate, and refuses to give medical advice.

Why it's hard: each regulator names additives differently (Europe uses an **E-number**, the US FDA uses chemical names, cancer researchers use another scheme), and no ready-made table links them. The one shared identifier is the **CAS number**, a globally unique ID for a chemical. Matching every additive across sources by CAS is the core engineering work, and it's what lets the app answer questions a generic chatbot can't.

## Quick Start

The additive database and the vector index are already built and committed, so **you don't need to run any build scripts to use the app**. Two steps: install, then run.

```bash
cd ~/code/courses/label_lens
uv sync                                          # install dependencies (Python 3.13 via uv)
uv run streamlit run streamlit_app.py            # opens http://localhost:8501
```

The chat app needs one key to answer questions: put `OPENROUTER_API_KEY=...` in a `.env.local` file at the repo root before running. (Optional: `OPENROUTER_MODEL` to pick the model, `LANGSMITH_API_KEY` to trace each run, `SHOW_ACTIVITY_LOG=1` to show the session-wide activity log at the foot of the app; it is hidden by default.)

Prefer the command line? Ask the agent one question directly:

```bash
uv run python scripts/ask.py "Why did the EU ban titanium dioxide, and does that mean it's dangerous?"
```

The agent routes each question to the right lane: a **Store** lookup (DuckDB) for legal facts, **RAG** over the briefs for evidence, or a **live** government API (openFDA recalls, Federal Register bans). It cites every claim and refuses medical verdicts.

### Rebuilding the database from scratch (optional, not needed to run)

The four build scripts below regenerate `data/label_lens.duckdb` and the Chroma index. They already ran once and their output is committed, so run these **only** if you want to rebuild.

```bash
uv run python scripts/build_spine.py      # build the additive database -> data/label_lens.duckdb
uv run python scripts/load_products.py    # load US candy products from Open Food Facts
uv run python scripts/build_briefs.py     # generate the per-additive briefs (needs OPENROUTER_API_KEY)
uv run python scripts/build_index.py      # embed the briefs into the Chroma vector index
```

No API keys are needed for `build_spine` or `build_index`; `build_briefs` needs `OPENROUTER_API_KEY`. Heads-up: `load_products.py` calls the public Open Food Facts API, which is now behind bot protection and may return **401/503**. That failure only affects rebuilding the product table, not running the app against the committed database.

Once built (or using the committed database), query it directly:

```bash
uv run python - <<'PY'
from label_lens.db import connect
con = connect()
for row in con.execute(
    "SELECT r.jurisdiction, r.status, r.citation FROM additives a "
    "JOIN regulatory_status r USING(cas) WHERE a.e_number='E171'").fetchall():
    print(row)   # E171: banned in the EU, permitted by the US FDA, not a dietary cancer classification
PY
```

## Documentation

| Doc | What it's for |
|---|---|
| **[docs/RUBRIC.md](./docs/RUBRIC.md)** | The official grading rubric (100 points) and the coverage checklist: every deliverable, its points, where it's answered, and its status. **Start here to review coverage.** |
| **[docs/deliverables.md](./docs/deliverables.md)** | The Certification Challenge write-up: the answer to every graded deliverable, one section per task. |
| **[docs/TECH_DESIGN.md](./docs/TECH_DESIGN.md)** | How the system is built and why: architecture, the technology choices and their tradeoffs, and how the database is assembled. |
| **[PLAN.md](./PLAN.md)** | Where the project stands and what's next, in build order. |
