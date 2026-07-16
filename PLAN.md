# Label Lens: Roadmap & Status

Where the project stands and what's built next, in dependency order. For *how and why* the system is designed, see [`docs/TECH_DESIGN.md`](./docs/TECH_DESIGN.md). For the certification deliverables and their per-item status, see the coverage checklist in [`docs/RUBRIC.md`](./docs/RUBRIC.md#coverage-checklist).

## Where we are

**Built:** the CAS store (28 additives resolved to CAS + 64 cited regulatory-status rows), the **28-brief RAG corpus** in `data/briefs/` (committed), **100 US candy products** in the `product` table, the **Chroma vector index** over the briefs, the **working LangGraph agent** (four tools: Store / RAG / openFDA / Federal Register, + user memory, every model call through OpenRouter, LangSmith tracing when a key is set), and the **Streamlit chat UI** (`streamlit_app.py`, deploy-ready for Community Cloud). All six eval question types return cited answers locally. See the [Quick Start](./README.md#quick-start).

**Status coverage:** every in-scope additive (28/28) now has EU and US FDA regulatory-status rows, plus California / IARC rows where a notable ruling or classification exists. Each was primary-source-verified (21 CFR sections against eCFR / Cornell LII, EU rulings against EUR-Lex, IARC groups against the named monographs). The affected briefs were regenerated so the RAG corpus matches the store. Caveat: the recorded eval baseline predates this fill (see Milestone 4).

**Also built:** the **evaluation harness** (Milestone 4). A 22-question gold set (`evals/gold.jsonl`), an LLM-judge (correctness / groundedness / safety), RAGAS (context precision/recall, faithfulness, answer relevancy), and a retrieval before/after comparison. Baseline recorded in `evals/results.json`; the reranker lifts Hit@1 0.75 → 0.85 and MRR 0.81 → 0.90, hybrid BM25+dense also lifts Hit@1 to 0.85. Tasks 5 and 6 answered with numbers in deliverables.

**Deployed:** live and public at https://label-lens.streamlit.app/ (Streamlit Community Cloud), password-gated to protect the LLM key, opens on phone and laptop. Task 7 reflection written. The repo is public.

**All deliverables complete**, including the ≤10-minute Loom demo (linked at the top of [deliverables.md](./docs/deliverables.md)).

### Status: complete

Every rubric deliverable is done. The Loom demo is recorded and linked at the top of [deliverables.md](./docs/deliverables.md), and the eval was re-run at full 28/28 status coverage (`evals/results.json`, written up in deliverables §5-6).

Notes for a fresh clone: the DuckDB store (`data/label_lens.duckdb`) and the Chroma index (`data/chroma/`) are local and gitignored, so rebuild them with `build_spine.py` then `load_products.py` then `build_briefs.py` then `build_index.py`. Open Food Facts' API is intermittently flaky (503); the loader uses the reliable category-based query and retries, but a small batch (`load_products.py 100`) is more likely to slip through than 400. The OpenRouter key is in `.env.local` (gitignored, stays on this machine).

## The plan

Five milestones in dependency order (each one needs the previous). No dates: this is the build order, not a calendar. Every milestone lists its goal, what it produces, the certification deliverables it closes, and the concrete condition that means it's done. Per-deliverable status lives in the [coverage checklist](./docs/RUBRIC.md#coverage-checklist).

### Milestone 1: Data and briefs

**Status: done.** Briefs built (28); 100 US candy products loaded; status coverage 28/28 (EU + US FDA for every additive, California / IARC where a notable ruling exists).

**Goal:** turn the CAS spine into the knowledge the assistant reasons over.

- Load US candy / confectionery products from Open Food Facts into the `product` table.
- Extend the curated regulatory status so every in-scope additive has an EU / US FDA / California / IARC row (an explicit "no action recorded" row where that's the truth), keeping legal status and hazard separate.
- Generate one distilled brief per additive (identity / regulatory status / evidence), a citation on every claim; hand-verify a subset against primary sources.

**Produces:** a populated `product` table, the per-additive brief corpus, and the first version of the gold answer set.
**Closes:** Task 3 (chunking strategy, data source); seeds the eval questions for Task 1.4 and Task 5.1.
**Done when:** every in-scope additive has a brief, and a hand spot-check confirms its claims are cited and correct.

### Milestone 2: Retrieval and the agent

**Status: done.** Chroma index over the 84 brief chunks; LangGraph agent with the four tools + memory; every model call through OpenRouter; all six eval question types return cited answers locally, the cumulative question grounded in the real product→additive join.

**Goal:** a working end-to-end agent, running on the laptop.

- Embed the briefs into Chroma with `bge-small` (local, Apple Silicon); build the dense-retrieval baseline.
- Build the LangGraph agent with four tools: status-query (DuckDB), brief-retriever (RAG), openFDA recall, Federal Register ban; route each question to the right lane.
- Add memory: a per-user diet / allergy profile and a product log in DuckDB.
- Route every model call through OpenRouter; turn on LangSmith tracing.

**Produces:** a local agent that answers the six evaluation question types with cited answers.
**Closes:** Task 4 deliverable 1 (end-to-end prototype); the Task 2 requirements (gateway, memory, tools).
**Done when:** each of the six sample questions in [deliverables §1.4](./docs/deliverables.md#14-questions-we-evaluate-against) returns a cited answer locally, visible as a trace in LangSmith.

### Milestone 3: The app, in a browser, public

**Status: done.** The Streamlit chat app (`streamlit_app.py`) is built, driven headlessly by AppTest, and **deployed live at https://label-lens.streamlit.app/** (Community Cloud, password-gated to protect the LLM key, opens on phone and laptop).

**Goal:** make it usable and reachable, the cheap way.

- Wrap the agent in a Streamlit chat UI (enter a barcode, or ask about an additive).
- Deploy to Streamlit Community Cloud for a public URL that opens on phone and laptop.

**Produces:** a public demo URL.
**Closes:** Task 4 deliverable 2 (public deployment); the Task 2 requirement to run in a phone and laptop browser.
**Effort note:** small. Streamlit is responsive by default and Community Cloud is free hosting, so no phone-specific work is needed. Both are hard requirements in the challenge README (Task 2 and Task 4), so this stays in scope; dropping it would forgo the Task 4 deploy credit.
**Done when:** the public URL answers a question, including one live tool call, opened from a phone.

### Milestone 4: Evaluate, then improve with evidence

**Status: done.** 22-question gold set from the curated status rows; LLM-judge (correctness/groundedness/safety) + RAGAS harness with a recorded baseline; reranker and hybrid before/after tables showing measured Hit@1/MRR gains. Conclusions written in deliverables §5.3. Key finding: retrieval is the bottleneck (high faithfulness, lower recall), and the status-coverage gap caps correctness. Note: this baseline was recorded at 15/28 status coverage; that gap has since been closed (see "Where we are"), so a re-run would remeasure correctness against complete data.

**Goal:** the graded evaluation story.

- Finalise the gold set of question / expected-answer pairs.
- Build the harness: RAGAS retrieval metrics plus an LLM-as-judge for correctness, groundedness, and the safety boundary. Record the baseline.
- Add the reranker (`bge-reranker`); produce the before/after table on the gold set.
- Add hybrid BM25 + dense retrieval; measure the further gain.

**Produces:** a baseline number and two improvement tables.
**Closes:** Task 5 (dataset, harness, conclusions); Task 6 (advanced retriever, comparison table, one other change).
**Done when:** the tables show measured deltas against the baseline and the conclusions are written.

### Milestone 5: Package and submit

**Goal:** a submission a reviewer can check in minutes.

- Write the Task 7 reflection (what to keep and what to change for Demo Day).
- Fill in `docs/deliverables.md` end to end; confirm every coverage-checklist row is green.
- Record the 10-minutes-or-less Loom demo showing a live tool call and describing the use case.
- Final repo tidy; confirm it is public.

**Produces:** the complete submission (public repo, video, written document).
**Closes:** Task 7 and the final-submission requirements.
**Done when:** the coverage checklist is all `✅` and the video and repo links are in place at the top of `docs/deliverables.md`.
