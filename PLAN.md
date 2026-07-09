# Label Lens: Roadmap & Status

Where the project stands and what's built next, in dependency order. For *how and why* the system is designed, see [`docs/TECH_DESIGN.md`](./docs/TECH_DESIGN.md). For the certification deliverables and their per-item status, see the checklist in [`docs/SUBMISSION.md`](./docs/SUBMISSION.md).

## Where we are

**Built and working:** the CAS spine and the DuckDB store, the data foundation the rest depends on. 28 additives resolved from E-number to CAS (Open Food Facts taxonomy + Wikidata), plus 32 curated, cited regulatory-status rows. See the [Quick Start](./README.md#quick-start) to build and query it.

**Not yet built:** the distilled per-additive briefs, the vector index, the LangGraph agent and its tools, the user memory, the Streamlit UI, the public deployment, and the evaluation harness.

## What's next (in dependency order)

1. **Briefs.** Distil the per-additive intelligence briefs from the joined data; hand-verify the gold answer set against primary sources.
2. **Retrieval + agent.** Build the vector index and the dense-retrieval baseline; stand up the LangGraph agent with the Store, RAG, and Live tools plus user memory.
3. **App.** Wrap it in a Streamlit chat UI; deploy to a public URL that works on phone and laptop.
4. **Evaluate + improve.** Build the evaluation harness; record the baseline; add the reranker and hybrid retrieval and measure each gain.
5. **Finish.** Write the Task 7 reflection; record the demo video; finalise `docs/SUBMISSION.md`.

Granular, per-deliverable status lives in the [coverage checklist](./docs/SUBMISSION.md#coverage-checklist).
