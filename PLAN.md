# Label Lens — Project Plan

Label Lens is a food-additive **intelligence** app. You give it a packaged food, and it tells you what a barcode scanner can't: which of the additives inside are **banned or restricted in other countries**, what the **scientific evidence** actually says about them, and whether they're under a recall or a fresh government ban. Every answer is **cited** from official regulators.

This document is the engineering plan and the rationale behind every design choice, written so someone with no background in AI retrieval systems or in food chemistry can follow it. It is built to satisfy the AI Engineering Certification **Certification Challenge** (7 tasks, due 2026-07-14).

## Reviewers start here

The graded, deliverable-by-deliverable write-up lives in **[`docs/SUBMISSION.md`](./docs/SUBMISSION.md)**. It opens with a **coverage checklist**: one row per required deliverable, each linking to exactly where that deliverable is answered (a doc section, a code file, or an evaluation result). Read that table top to bottom to confirm nothing is missing, then click through. This `PLAN.md` is the "why and how" that the checklist links into for depth.

---

## Part 1 — The domain in one minute

**What is a food additive?** A substance mixed into packaged food for a purpose: **colours** (make candy bright), **preservatives** (stop it spoiling), **sweeteners** (sugar-free soda), **antioxidants** (keep fats from going rancid). They are useful. Preservatives prevent food poisoning and waste; colours and sweeteners make food people want to eat, often more cheaply.

**How they can hurt.** Some additives are contested. A few colours have been linked to hyperactivity in children. A handful are flagged as possible carcinogens. And regulators around the world disagree sharply: an additive that is normal in a US candy bar can be banned, or carry a warning label, in Europe.

**The honest framing this app is built around:** *"banned somewhere" is not the same as "proven harmful."* Often two regulators looked at the **same** evidence and made different judgment calls. Label Lens shows what each regulator decided **and** what the evidence says, keeps those two ideas separate, and refuses to give medical advice.

## Part 2 — The core engineering problem

To answer "is this additive banned in the EU?" you must combine data from several regulators. But each one **identifies additives differently**, and no ready-made table links them:

- **Europe** uses an **E-number** (a short code; titanium dioxide is `E171`).
- **The US FDA** uses chemical names and its own IDs.
- **Cancer researchers (IARC)** use yet another naming scheme.

The one identifier they can all share is the **CAS number**, a globally unique ID for a chemical substance (titanium dioxide is `13463-67-7`). So the core engineering task is **matching each additive across every source using CAS as the common key**. No single database and no off-the-shelf chatbot can hand you this; building it is the project's moat, and it is what makes the app do something a generic AI cannot.

---

## Part 3 — The solution and its architecture (Task 2)

**One-sentence solution:** an agentic RAG assistant that, given a product's additives, answers plain-language questions by routing each one to the right source and returning a cited, regulator-grounded answer.

The assistant routes every question to one of **three lanes**:

| Lane | What it holds | Example question | How it answers |
|---|---|---|---|
| **Store** | Structured facts: each additive's legal status per region (a database table) | "Is E171 banned in the EU?" | a direct database lookup (a tool call) |
| **RAG** | Distilled **per-additive briefs**: prose explaining the regulatory divergence and what the evidence says | "Why did the EU ban it, and is it actually dangerous?" | retrieve the relevant brief passages, answer from them |
| **Live** | Nothing stored; calls government APIs at question time | "Is this recalled? Any FDA action this month?" | live external API call |

The **RAG lane is the heart of the project** (it holds knowledge that exists in no single database), and it is where the evaluation story lives. The Store and Live lanes make the assistant **agentic**: it decides which tool to call.

### The technology choices, and why each one

Every component below is a required item in the Certification Challenge's infrastructure list. The "why" is the one-line justification the challenge asks for.

| Component | Choice | Why this choice |
|---|---|---|
| **LLM gateway** | **OpenRouter** | The challenge requires routing model calls through a gateway rather than a raw provider. OpenRouter is one key, many swappable models, minimal code. |
| **LLM** | a strong general model via OpenRouter (configurable) | The gateway makes the specific model swappable; we tune for cost vs quality during evals. |
| **Agent orchestration** | **LangGraph** | Purpose-built for an agent that reasons, routes to tools, and carries memory; integrates with our tracing. |
| **Tools** | status-query (database), brief-retriever (RAG), openFDA-recall, Federal-Register-ban | These realise the three lanes; the two live government APIs are the required external search. |
| **Embedding model** | **bge-small-en-v1.5**, run locally on the Mac (Apple Silicon / MPS) | The brief corpus is tiny, so a small local model is free, fast, and needs no external API. |
| **Vector database** | **Chroma** (a local file, no server) | Simplest possible vector store for a small corpus; nothing to run or host. |
| **Monitoring** | **LangSmith** | Traces every agent step and retrieval so we can debug and back the evaluation story with real run data. |
| **Evaluation framework** | **RAGAS** + a prompted **LLM-as-judge** | RAGAS scores retrieval quality; the judge scores whether the final answer is correct, grounded, and safe. |
| **User interface** | **Streamlit** | One Python file gives a chat UI that works in a phone and laptop browser (both required). |
| **Deployment** | **Streamlit Community Cloud** | Free public URL, which satisfies the public-endpoint requirement and the phone requirement together. |
| **Structured store** | **DuckDB** | A lightweight local database holding the additive and regulatory-status tables (already built). |

### How a question flows through the app (the agent workflow)

1. The user asks a question about a product (or one of its additives) in the chat UI.
2. The **LangGraph agent** reads the question and its **memory** (the user's saved diet/allergy profile and logged products) and decides which lane(s) to use.
3. For a legal-status fact, it calls the **Store** tool (a database query). For a "why / is it dangerous" question, it **retrieves** the relevant per-additive brief passages (**RAG**). For "is this recalled / any recent ban," it calls a **Live** government API.
4. It composes a single cited answer, keeping legal status, hazard classification, and personal harm strictly separate, and refusing medical verdicts.
5. The answer is returned in the browser. (No human approval step is required; the safety boundary is enforced in the prompt and the routing.)

The rendered infrastructure and agent-workflow diagrams live in `docs/SUBMISSION.md` §2.

### Required capabilities, and where they are met
- **LLM gateway:** OpenRouter (above).
- **Memory:** a per-user diet/allergy profile plus a log of products they've asked about, stored in DuckDB, so the agent can answer cumulative questions ("across everything I logged today, am I over any safe limit?").
- **Runs on phone and laptop in a browser:** Streamlit UI on a public Community Cloud URL.

---

## Part 4 — The data, and how it's built (Task 3)

### Our own data: the per-additive briefs (the RAG corpus)

The retrievable knowledge is a set of **per-additive intelligence briefs**: for each additive, a short structured document covering its **identity** (names, codes, CAS), its **regulatory status** in each region with citations, and the **evidence** (why a regulator acted, what the safety assessments found). This is distilled by an LLM from the joined regulatory data, with a citation on every claim, then hand-checked against primary sources.

These briefs are built on top of the **CAS spine** that already exists: 28 additives resolved from E-number to CAS by combining the Open Food Facts additives taxonomy (names, codes) with Wikidata (the CAS numbers), stored in DuckDB alongside curated, cited regulatory-status rows. See [`README.md`](./README.md) for how to build and query it.

### Chunking strategy (and why)

**One brief per additive, split on its labelled sections** (identity / regulatory status / evidence). We chose section-based chunks rather than fixed-size chunks because the user's questions map cleanly onto those sections ("is it banned" → status section; "is it dangerous" → evidence section), which keeps each retrieved passage self-contained and its citation intact. The corpus is small enough that this stays simple.

### External data / API (the agentic search)

The agent searches **live public data** through two government APIs at question time: **openFDA food enforcement** (product recalls) and the **Federal Register** (newly published bans and revocations). These satisfy the challenge's "search publicly available data" requirement and keep answers current in a way a static store cannot. A general web-search tool (e.g. Tavily) is an easy later add if a broader search is wanted.

---

## Part 5 — Evaluation and improvement (Tasks 5 and 6)

### Baseline evaluation (Task 5)
- **Test dataset:** a gold set of question / expected-answer pairs, grounded in the curated, cited regulatory rows (which double as ground truth).
- **Harness:** RAGAS for retrieval quality (did we fetch the right brief passages?) plus a prompted LLM-as-judge for the final answer (is it correct, grounded in the citation, and safe, meaning it never conflates *banned* with *hazardous* with *harmful*?).
- We record a **baseline** number before any tuning.

### Measured improvements (Task 6)
- **Advanced retriever:** add a **reranker** (bge-reranker, run locally) on top of the dense-retrieval baseline. Rationale: it should better separate near-identical briefs (for example the two preservatives E210 and E211). We report a **before/after table** on the gold set.
- **One other change:** **hybrid retrieval** (combine keyword BM25 search with dense search). Rationale: questions contain exact tokens (E-numbers, CAS numbers, "21 CFR") that keyword search matches and pure meaning-based search can miss. Again measured on the gold set.

---

## Part 6 — Safety boundary (built into the data, not bolted on)

**Legal status ≠ hazard classification ≠ personal harm. Not medical advice.** The app reports what regulators decided and what the evidence says; it refuses health verdicts and never conflates the three. This is enforced in the data schema (legal status and hazard are separate columns) and in the agent's prompt, and it is one of the things the evaluation judge checks.

## Part 7 — Deployment and access (Task 4)

The finished prototype is a Streamlit chat app deployed to Streamlit Community Cloud, giving a public URL that works in a phone or laptop browser. The demo shows a **live** tool call (a real recall or ban lookup), not a cached table.

---

## Scope and current state

**Scope (deliberately small, so the cross-source join is hand-verifiable):** 28 additives (mostly synthetic colours, plus marquee preservatives, sweeteners, and the California-banned set), within one product category, **US candy / confectionery**.

**Built and working today:** the CAS spine and the DuckDB store (the 28 additives resolved to CAS, plus 32 curated, cited regulatory-status rows). This is the foundation the briefs and the eval gold set are built from.

**Still to build:** the distilled briefs, the vector index, the LangGraph agent and its tools, the user memory, the Streamlit UI, the public deployment, and the evaluation harness.

## Roadmap (ordered by dependency, not by calendar)

1. Distil the per-additive briefs from the joined data; hand-verify the gold set.
2. Build the vector index and the dense-retrieval baseline; stand up the LangGraph agent with the Store, RAG, and Live tools and user memory.
3. Wrap it in the Streamlit UI; deploy to a public URL.
4. Build the evaluation harness; record the baseline; add the reranker and hybrid retrieval and measure the gains.
5. Write the Task 7 reflection; record the demo video; finalise `docs/SUBMISSION.md`.

Progress against every individual deliverable is tracked in the checklist at the top of [`docs/SUBMISSION.md`](./docs/SUBMISSION.md).
