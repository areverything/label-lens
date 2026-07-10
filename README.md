# Label Lens

Scan a packaged food and understand its additives: which ones are **banned or restricted in other countries**, what the **scientific evidence** actually says, and whether any are under a recall or a fresh government ban. Every answer is cited from official regulators. This is an AI Engineering Certification capstone.

## What are food additives?

Additives are substances mixed into packaged food for a purpose: **colors** (make candy bright), **preservatives** (stop it spoiling), **sweeteners** (sugar-free soda), **antioxidants** (keep fats from going rancid). They're useful. Preservatives prevent food poisoning and waste; colors and sweeteners make food people want to eat, often more cheaply.

The catch is that some are *contested*. A few colors have been linked to hyperactivity in children; a handful are flagged as possible carcinogens; and regulators disagree sharply, so an additive that's normal in a US candy bar may be banned, or carry a warning label, in Europe. **"Banned somewhere" is not the same as "proven harmful"**: often two regulators looked at the same evidence and made different calls. Label Lens shows what each regulator decided and what the evidence says, keeps those two things separate, and refuses to give medical advice.

Why it's hard: each regulator names additives differently (Europe uses an **E-number**, the US FDA uses chemical names, cancer researchers use another scheme), and no ready-made table links them. The one shared identifier is the **CAS number**, a globally unique ID for a chemical. Matching every additive across sources by CAS is the core engineering work, and it's what lets the app answer questions a generic chatbot can't.

## Quick Start

```bash
cd ~/code/courses/label_lens
uv sync                                   # install dependencies (Python 3.13 via uv)
uv run python scripts/build_spine.py      # build the additive database -> data/label_lens.duckdb
uv run python scripts/load_products.py    # load US candy products from Open Food Facts
uv run python scripts/build_briefs.py     # generate the per-additive briefs (needs the LLM key)
uv run python scripts/build_index.py      # embed the briefs into the Chroma vector index
```

Then ask the agent a question (needs `OPENROUTER_API_KEY` in `.env.local`):

```bash
uv run python scripts/ask.py "Why did the EU ban titanium dioxide, and does that mean it's dangerous?"
```

Or open the chat app in a browser (phone or laptop):

```bash
uv run streamlit run streamlit_app.py            # opens http://localhost:8501
```

The agent routes each question to the right lane: a **Store** lookup (DuckDB) for legal facts, **RAG** over the briefs for evidence, or a **live** government API (openFDA recalls, Federal Register bans). It cites every claim and refuses medical verdicts. Set a LangSmith key (`LANGSMITH_API_KEY`) to see each run traced.

This builds a table of additives (each linked to its CAS number) plus their legal status per region, and prints a coverage report. Query it:

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

No API keys are needed to build the database. An LLM key (for the question-answering features) goes in `.env.local`.

## Documentation

| Doc | What it's for |
|---|---|
| **[docs/RUBRIC.md](./docs/RUBRIC.md)** | The official grading rubric (100 points) and the coverage checklist: every deliverable, its points, where it's answered, and its status. **Start here to review coverage.** |
| **[docs/SUBMISSION.md](./docs/SUBMISSION.md)** | The Certification Challenge write-up: the answer to every graded deliverable, one section per task. |
| **[docs/TECH_DESIGN.md](./docs/TECH_DESIGN.md)** | How the system is built and why: architecture, the technology choices and their tradeoffs, and how the database is assembled. |
| **[PLAN.md](./PLAN.md)** | Where the project stands and what's next, in build order. |
