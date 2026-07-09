# Label Lens — Build Plan

A food-additive **intelligence** RAG app. Scan a product and ask what a scanner can't answer: which additives are **banned somewhere else**, what the **evidence** actually says, and whether you're **over a safe limit across your day**. Cited from the open food catalog, four regulators, and a distilled brief that lives in no single database.

This is the AI Engineering Certification capstone (due **2026-07-14**). The full rationale and the runner-up ideas live in the Obsidian vault at `AI Engineering Certification v1.0/Capstone — Build Kickoff (Label Lens).md`. This file is the buildable plan; it is self-contained, so a fresh session can work from it alone.

## Quick Start

```bash
cd ~/code/courses/label_lens
uv init .
uv add langgraph langchain langchain-community duckdb httpx pandas openpyxl rank-bm25 fastapi "uvicorn[standard]" python-dotenv
uv add --dev ragas pytest
# LLM gateway key (OpenRouter or similar) goes in .env.local
```

Then open a **new Claude Code session in this folder** and paste the kickoff prompt at the bottom of this file. Day 1 is the data join, not the app.

## The one thing that matters

**The join is the whole project.** No pre-built cross-walk maps the same additive across the EU, FDA, IARC, and California. Each regulator keys its data differently:

- **E-number** (EU, Open Food Facts)
- **CAS number** (FDA, IARC, EFSA OpenFoodTox)
- **FDA substance name**, **IARC agent name**

Reconciling these into **one canonical additive** is the engineering, and it is the moat: no single source and no base model can hand it to you. **CAS number is the join key.** Open Food Facts + OpenFoodTox both carry E-number *and* CAS, so they bridge everything else.

Second rule, baked into the schema: keep **legal status** (FDA / EU / California) separate from **hazard assessment** (EFSA / IARC). They answer different questions, and conflating them breaks the safety boundary ("banned somewhere" ≠ "proven harmful").

## Architecture: Document D is two layers + live tools

The retrievable unit is a **per-additive intelligence brief**. An agent routes each question to one of three lanes:

| Lane | What it is | Example question | Graded by |
|---|---|---|---|
| **Store** (query) | Product facts + a per-additive **legal-status table** (one row per additive × jurisdiction) | "Is E171 banned in the EU?" | tool-call accuracy |
| **RAG** (retrieval) | Distilled **regulatory-divergence + evidence prose** | "Why did the EU ban it, and is it actually dangerous?" | the retrieval ladder |
| **Live** (tools) | openFDA recalls + Federal Register new bans | "Is this recalled? Any FDA action since last month?" | tool-call accuracy |

The **RAG lane is the real value-add** and where the retrieval-ladder eval story lives. The store and live lanes make it agentic.

### Additive-brief schema

- **Identity** — `e_number`, `name`, `additives_classes`, **CAS** (from OFF additives taxonomy).
- **Regulatory status** — one row per jurisdiction: EU (Reg 1333/2008 + ban amendments), US/FDA (Substances Added to Food + 21 CFR), California (Prop 65 + AB 418's four additives), IARC (hazard group, flagged hazard-not-law).
- **Evidence** — EFSA ADI (OpenFoodTox, structured) + reasoning distilled from EFSA opinions; IARC group + exposure route.
- **Live watch** — recall status (openFDA), new Federal Register action.

> **Worked example (real as of 2026):** Titanium dioxide (E171, CAS 13463-67-7). EU **banned in food since 2022** (Reg (EU) 2022/63) after EFSA's 2021 opinion withdrew the ADI over nanoparticle genotoxicity; **FDA still permits it** (21 CFR 73.575); IARC Group 2B is for **inhaled** dust, not diet. Honest brief: regulators weighed the same evidence differently, not settled-dangerous.

## Data sources (verified 2026-07-08)

| Source | Feeds | Difficulty | Access |
|---|---|---|---|
| **Open Food Facts** products + additives taxonomy | The spine (E-number↔CAS↔class), product facts | Easy | Parquet on HF (filter w/ DuckDB) + v2 barcode API; no key, User-Agent; ODbL. Taxonomy: `static.openfoodfacts.org/data/taxonomies/additives.json` |
| **FDA Substances Added to Food + SCOGS** | US legal/GRAS status, 21 CFR cite, CAS | Easy | Excel export, CFSAN portal; public domain |
| **Federal Register + eCFR Title 21** | Bans/revocations (Red 3, BVO); current code; **live ban tool** | Easy | Free JSON/CSV API, no key (`federalregister.gov/developers`, `ecfr.gov/developers`) |
| **IARC classifications** | Cancer-hazard group (thin coverage) | Easy | Sortable spreadsheet by agent/group/CAS |
| **California OEHHA** | Prop 65 list + AB 418 (4 additives) | Easy | Prop 65 Excel; AB 418 hardcoded from bill |
| **EFSA OpenFoodTox** | Structured ADI/hazard; reasoning in PDFs | Medium | DB on Zenodo (v3.0, Apr 2026) + EFSA Journal PDFs |
| **EU Reg 1333/2008 Annex II** | EU authorized-additive conditions | Medium | Consolidated EUR-Lex table; needs parsing |
| **openFDA food enforcement** | Recalls; **live tool** | Easy | `api.fda.gov/food/enforcement.json`, key optional (1000/day free). Matches by name not barcode (fuzzy), US-only |

Everything is open and no-cost. The effort is entity resolution, not downloads.

## Proposed stack

- **Python 3.12 via `uv`** (macOS Apple Silicon; use MPS for any local model).
- **Structured store + ETL:** DuckDB (also does the OFF Parquet filtering) or SQLite. One canonical `additives` table keyed by CAS; a `product` table; a `user_profile` + `pantry` table for memory.
- **Agent + tools:** LangGraph. Tools = status-query, brief-retriever, openFDA-recall, federal-register-ban.
- **LLM gateway (rubric-required):** OpenRouter or LiteLLM.
- **Vector store + retrieval ladder:** Qdrant (local docker) or Chroma. Dense baseline → BM25/hybrid → reranker (Cohere API or local `bge-reranker` on MPS) → multi-query (LangChain `MultiQueryRetriever`) → parent-child (`ParentDocumentRetriever`).
- **Backend:** FastAPI. **Frontend:** keep it lean for the deadline (Streamlit for speed, or FastAPI + a small chat UI; must work on phone + laptop). Decide Day 3.
- **Deploy:** Render / Vercel / FastAPI Cloud (public endpoint required).
- **Eval:** Ragas + a hand-built gold set; LLM-as-judge for outcome, retrieval metrics per rung.

## Phased plan (the five-day cut)

**Scope first, small:** a few dozen high-interest additives (flagged colours, preservatives, sweeteners) and **one product category** (e.g. US snacks/cereals), so the cross-walk is hand-verifiable.

1. **Day 1 — Spine + join.** Build the E-number↔CAS spine from the OFF taxonomy. Pull FDA (Excel), EU, IARC, Prop 65; resolve entities into one canonical additive table keyed by CAS. Load product facts for the chosen category from OFF (DuckDB over Parquet). Output: a clean `additives` + `product` store you trust.
2. **Day 2 — Distill.** Generate the regulatory-divergence + evidence briefs (LLM over the joined data + EFSA reasoning), with provenance on every claim. Hand-verify a gold set against primary sources. This is the synthetic-data / distillation work.
3. **Day 3 — Baseline agent.** Dense RAG on briefs + status-query tool + live openFDA/Federal Register tools, LangGraph routing, pantry memory, browser UI, deploy. Establish the baseline eval number.
4. **Day 4 — Climb + eval.** Add hybrid/BM25, reranker, parent-child; measure each rung on the gold set; build the tradeoff table (the graded improvement).
5. **Day 5 — The ablation + write-up.** Brief-RAG vs a live agent reading raw regulator pages: accuracy, cost, latency, and how stale a base model is on current bans. Record the video.

## Eval questions mapped to the ladder

- **BM25/hybrid:** "Is E171 banned in the EU?" (exact E-number + jurisdiction tokens)
- **Reranking:** distinguish two similar preservative briefs (E211 vs E210)
- **Multi-query:** "is this dye sketchy?" → additive + its four regulators + evidence
- **Parent-child:** retrieve the additive brief, attach the scanned product
- **Multi-hop (memory):** "across everything I logged today, am I over any ADI?"
- **Refusal/faithfulness:** "will this hurt me?" → status + evidence, keep banned/hazard/harmful distinct, refuse medical advice

## Safety boundary (bake into the schema, not bolt on)

**Banned somewhere ≠ proven harmful. Legal status ≠ hazard ≠ harm. Not medical advice.** The app reports what regulators decided and what the evidence says; it refuses health verdicts and never conflates the three.

## Decisions to make before writing code

1. **The additive slice** (which families) and **the one product category**. Smaller than feels comfortable.
2. **Canonical ID** = CAS, with an E-number and FDA-name alias table. Confirm the OFF/OpenFoodTox bridge covers your slice.
3. **Frontend choice** (Streamlit vs FastAPI + chat UI) given the deadline.

## Kickoff prompt for a new session

> I'm building my AIEC capstone: **Label Lens**, a food-additive intelligence RAG app, in this folder (`~/code/courses/label_lens`). Read `PLAN.md` first, it's the full plan. Document D is a per-additive brief with two layers: a structured store (product facts + a per-additive legal-status table across EU/FDA/California/IARC) and a RAG corpus (distilled regulatory-divergence + evidence prose), plus live openFDA recall and Federal Register ban tools. The core challenge is entity resolution (E-number ↔ CAS ↔ FDA name ↔ IARC name), CAS is the join key. Start me on **Day 1: pick the additive slice + product category with me, then build the E-number↔CAS spine from the OFF additives taxonomy and join FDA + EU + IARC + Prop 65 into one canonical additive table.** Set up the `uv` environment and the ETL scaffolding.
