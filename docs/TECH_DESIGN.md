# Label Lens: Technical Design

How the system is built and why. This is the home for architecture, the technology tradeoffs, and the data pipeline. It assumes you've read the [README](../README.md) for what the project is and the domain. The certification write-up ([SUBMISSION.md](./SUBMISSION.md)) links here for depth; the diagrams live there (they're graded deliverables) and are referenced below.

## Architecture: three lanes

The assistant answers every question by routing it to one of three lanes, each backed by a different kind of source. The split exists because the questions fall into three kinds that need different machinery:

| Lane | Holds | Answers questions like | Mechanism |
|---|---|---|---|
| **Store** | Structured facts: each additive's legal status per region, in a database table | "Is E171 banned in the EU?" | a direct database query (a tool call) |
| **RAG** | Distilled **per-additive briefs**: prose on the regulatory divergence and the evidence | "Why did the EU ban it, and is it actually dangerous?" | retrieve the relevant brief passages, answer from them |
| **Live** | Nothing stored; government APIs called at question time | "Is this recalled? Any FDA action this month?" | a live external API call |

The **RAG lane is the core of the project**: it holds distilled knowledge that exists in no single database, and it is where the evaluation story lives. The Store and Live lanes make the assistant **agentic**, it decides which tool to call. The runtime flow of a single request (input → routing → tools → answer) is the agent-workflow diagram in [SUBMISSION §2.3](./SUBMISSION.md#23-agent-workflow); this section is the static "why it's shaped this way."

## The data pipeline: how the database is built

The structured Store and the RAG briefs are both built on one foundation: a canonical additive table keyed by CAS number. Building it is the hard part, because no source carries every identifier.

1. **Names and codes** come from [Open Food Facts](https://openfoodfacts.org) (a free, crowd-sourced database of packaged foods). Its *additives taxonomy* maps each E-number to a name, a category, and a [Wikidata](https://www.wikidata.org) link.
2. **CAS numbers** are *not* in Open Food Facts (a discovery: the original plan assumed they were). They come from Wikidata, which stores a CAS number for each chemical. The bridge is therefore `E-number → Wikidata → CAS`. Two additives needed a hand override (documented in `src/label_lens/etl/spine.py`): erythrosine (the disodium salt CAS the FDA uses, not the acid form Wikidata returns) and brominated vegetable oil (a mixture with no single CAS in Wikidata).
3. **Legal status** per region (EU, US FDA, California, plus the IARC cancer classification) is currently a hand-curated, primary-source-cited set covering the marquee cases; it doubles as the evaluation answer key.

Everything lands in one [DuckDB](https://duckdb.org) file (a lightweight local database) with three tables:

- **`additives`**: one row per substance, keyed by CAS; the canonical spine.
- **`regulatory_status`**: one row per additive per region. Legal status is kept in its own column and **never mixed with hazard classification** (see Safety below).
- **`product`**: the scanned foods for the chosen category (not yet loaded).

To build and inspect it, see the [Quick Start](../README.md#quick-start).

### Chunking (for the RAG briefs)

**One brief per additive, split on its labelled sections** (identity / regulatory status / evidence). We chose section-based chunks over fixed-size chunks because user questions map cleanly onto those sections ("is it banned" → status; "is it dangerous" → evidence), so each retrieved passage is self-contained and keeps its citation intact. Fixed-size chunks would cut across a citation and mix a legal fact with an evidence claim, which is exactly the conflation the app must avoid. The corpus is small (tens of additives), so this stays simple and needs no elaborate hierarchy.

### Brief generation (the RAG corpus)

`scripts/build_briefs.py` writes one markdown brief per additive *after* the store is built (`build_spine.py` first). It is a deliberate split of deterministic rendering and a tightly-constrained LLM (`src/label_lens/briefs/`):

- **Identity** and **Regulatory status** are rendered straight from the `additives` and `regulatory_status` tables (`assemble.py` gathers `Facts`, `generate.py` prints the section), so they cannot be hallucinated and every status row keeps its citation.
- **Evidence** is the *only* LLM-written section. The model gets a *facts block* in which each line already carries its citation, under a strict system prompt: use only the provided facts, cite every claim, never invent a fact or citation, keep legal status / hazard / harm separate, give no medical advice, and if a jurisdiction has no row say it is "not yet compiled" rather than infer one. The call goes through the OpenRouter gateway; the model is swappable.
- Output is one `E###.md` per additive in `data/briefs/`, split on the `##` headings the chunker reads.

Traced for titanium dioxide: `slice.py` scope entry → OFF taxonomy (name, class, Wikidata QID `Q193521`) → Wikidata `P231` (CAS `13463-67-7`) → `spine.py` writes the `additives` row (flagged `ambiguous_cas`; Wikidata lists two CAS) → `regulatory_seed.py` writes three cited `regulatory_status` rows (EU banned, US permitted, IARC not-classified) → `assemble.py` reads them into `Facts` → `generate.py` renders Identity + Status from the table and sends the cited facts block to the LLM for the Evidence prose → `data/briefs/E171.md`.

## Technology choices and tradeoffs

The per-component list with a one-line justification each (a graded deliverable) is in [SUBMISSION §2.2](./SUBMISSION.md#22-infrastructure). This section covers only the choices that deserve more than a sentence.

- **Vector store, Chroma over Qdrant.** The brief corpus is tiny, so an embedded, file-based store with nothing to run or host beats a server like Qdrant. If the corpus grew by orders of magnitude, Qdrant's filtering and scale would justify the operational cost; here they don't.
- **Briefs as individual markdown files, over one document or PDFs.** One `.md` per additive (split into three sections) keeps each retrieved passage mapped to exactly one additive and one section, so its citation and identity stay intact and a correction touches one small, git-diffable file; a single monolith would force chunk boundaries that straddle additives or blend a legal fact with an evidence claim. Markdown over PDF because the briefs *are* the retriever's text (no lossy PDF extraction step), the `#` / `##` headings are what the chunker parses (a PDF's layout is visual, not structural), and `.md` diffs cleanly in review where a PDF is an opaque binary. A PDF would only make sense if a source of truth were itself a PDF; here we generate the corpus, so we generate it in the format the pipeline consumes.
- **Embeddings and reranking, local via ONNX over an API.** `bge-small` embeddings (and later the `bge-reranker`) run locally through fastembed's ONNX runtime, no torch and no external API. ONNX on CPU is fast enough because the corpus and the per-query candidate set are tiny, and it keeps the deploy light: torch's default Linux wheel drags in ~2 GB of CUDA libraries that a CPU-only free-tier host neither needs nor can afford, so avoiding torch is what makes the same code run unchanged locally and on Streamlit Community Cloud. The retrieval ladder stays cost-free and offline-capable; the only calls that must go through the paid gateway are the LLM's.
- **LLM gateway, OpenRouter.** The certification requires routing model calls through a gateway rather than a raw provider. OpenRouter gives one key and swappable models behind a single endpoint with minimal code, which lets us tune the model for cost vs quality during evals without touching application code.
- **UI + deployment, Streamlit + Community Cloud.** One design decision satisfies three requirements at once: a browser UI, one that works on phone and laptop, and a public endpoint. Streamlit is a single Python file; Community Cloud gives a free public URL. A hand-built FastAPI + frontend would offer more control over streaming but costs far more code for the same graded outcome.
- **Retrieval improvements, reranker then hybrid.** The baseline is dense (meaning-based) retrieval. The reranker is added first because it directly fixes the likeliest failure: confusing near-identical briefs (for example the two preservatives E210 and E211). Hybrid (keyword BM25 fused with dense) is the second change because the questions contain exact tokens (E-numbers, CAS numbers, "21 CFR") that keyword search matches and pure meaning-based search can miss. Each is measured on the gold set (see [SUBMISSION Task 6](./SUBMISSION.md#task-6-improving-the-prototype)).

## Safety boundary (designed in, not bolted on)

**Legal status ≠ hazard classification ≠ personal harm. Not medical advice.** This is enforced in two places, not left to the model's goodwill:

- **In the schema:** `regulatory_status` keeps a jurisdiction's *legal* decision (banned / permitted / restricted) separate from the IARC *hazard* classification. A row can never assert "banned" and "carcinogenic" as the same fact.
- **In the agent:** the prompt requires the answer to report status and evidence separately, and to refuse a health verdict ("will this hurt me?") while still giving the facts. The evaluation judge checks this boundary explicitly.

## Scope

Deliberately small, so the cross-source join is hand-verifiable: **28 additives** within **one product category, US candy / confectionery**.

**Where the 28 come from.** They are a **hand-selected list** in `src/label_lens/slice.py`, not drawn from a dataset. Each additive earns its place by a *regulatory hook* recorded next to it: a specific reason regulators disagree, or a notable hazard classification. They cluster into:

- **Synthetic colours** (11): the sharpest EU / FDA / California divergence, including the "Southampton Six" child-hyperactivity dyes (E102, E110, E129, ...), titanium dioxide (E171, EU-banned but FDA-permitted), and erythrosine (E127, FDA-revoked 2025). Two low-divergence controls (E132, E133) are included on purpose.
- **Preservatives** (7): nitrites/nitrates (cured-meat / IARC processed-meat context), sulfur dioxide, and the benzoic-acid / sodium-benzoate pair (E210, E211) kept as a near-duplicate retrieval-reranking test.
- **Antioxidants** (2): BHA (IARC 2B, Prop 65) and BHT.
- **Sweeteners** (5): aspartame (IARC 2B, 2023), cyclamates (FDA-banned 1969), saccharin, and others.
- **The non-colour members of California's AB 418 (2023) ban** (3): propylparaben, brominated vegetable oil, potassium bromate.

So the *scope* is curated by hand (chosen for regulatory divergence and for the evaluation design), while the *chemistry* is resolved from Open Food Facts + Wikidata and the *legal status* comes from primary regulator sources: curated selection, sourced-and-cited facts. Small scope is a feature here: it lets every CAS match and every cited status row be checked by hand, which is what makes the app trustworthy rather than plausible.

## Repository layout

```
src/label_lens/
  slice.py              # the 28 additives in scope, and why each is interesting
  config.py  db.py  schema.sql
  etl/
    off_taxonomy.py     # Open Food Facts: E-number -> name, category, Wikidata id   [working]
    wikidata.py         # Wikidata: CAS numbers                                       [working]
    spine.py            # match everything into one table, with CAS overrides         [working]
    regulatory_seed.py  # curated, cited legal-status rows                            [working]
    fda.py eu.py iarc.py prop65.py off_products.py   # bulk data loaders              [scaffolded]
scripts/build_spine.py  # builds the database
docs/                   # SUBMISSION.md, TECH_DESIGN.md
```
