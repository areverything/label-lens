# Certification Challenge Rubric and Scorecard

The official grading rubric this submission is scored against, ingested verbatim, plus a task-level scorecard of how we're tracking. **100 points total.** (Course guidance: 85+ passes; below that you're asked to revise up, not failed.)

This doc is the **rubric and the coverage tracker**: the points reference plus the [coverage checklist](#coverage-checklist) below, which tracks where each deliverable is answered and its status. The answers themselves live in [SUBMISSION.md](./SUBMISSION.md).

## The rubric (verbatim)

| Task | Name | Pts | Deliverable |
|---|---|--:|---|
| 1 | Defining your Problem, Audience, and Scope | 1 | Write a succinct 1-sentence description of the problem |
| 1 | | 3 | Write 1-2 paragraphs on why this is a problem for your specific user |
| 1 | | 3 | Create a workflow diagram illustrating how the user solves this problem today |
| 1 | | 2 | Create a list of questions or input-output pairs to evaluate your application |
| 2 | Propose a Solution | 1 | Describe your solution in one sentence |
| 2 | | 7 | Create an infrastructure diagram of your stack; one sentence on why you made each tooling choice |
| 2 | | 7 | Create an Agent Workflow Diagram of how your application solves the user's problem end to end |
| 3 | Dealing with the Data | 5 | Describe all of your data sources and external APIs, and what you'll use them for |
| 3 | | 5 | Describe the default chunking strategy you will use. Why did you make this decision? |
| 4 | Build End-to-End Prototype | 15 | Build an end-to-end prototype and deploy with a front end using a tool like Vercel |
| 5 | Evals | 2 | Prepare a test data set (synthetic or assembled) |
| 5 | | 10 | Create an evaluation harness relevant to your problem space |
| 5 | | 3 | What conclusions can you draw about the performance and effectiveness of your pipeline? |
| 6 | Improving Your Prototype | 6 | Choose and implement an advanced retrieval technique; 1-2 sentences on why it will help |
| 6 | | 2 | How does performance compare to your original RAG application? Provide results in a table |
| 6 | | 6 | Implement a change to at least one other piece; use the eval harness to show a meaningful improvement |
| 7 | Next Steps | 2 | What will you keep for Demo Day, and what would you change or improve? |
| Final | Public GitHub Repo | 10 | A 10-minute (or less) Loom video: a live demo that also describes the use case |
| Final | | 10 | A written document addressing each deliverable and answering each question |
| Final | | 0 | All relevant code |
| | | **100** | **Total** |

## Points by task

| Task | Max points |
|---|--:|
| 1. Problem, Audience, Scope | 9 |
| 2. Propose a Solution | 15 |
| 3. Dealing with the Data | 10 |
| 4. End-to-End Prototype | 15 |
| 5. Evals | 15 |
| 6. Improving the Prototype | 14 |
| 7. Next Steps | 2 |
| Final Submission | 20 |
| **Total** | **100** |

## Coverage checklist

Every scored deliverable, its points, where it's answered in [SUBMISSION.md](./SUBMISSION.md), and its status. `✅` done · `🔨` drafted / in progress · `☐` not started. This is the single tracker; SUBMISSION.md holds the answers themselves.

| Task | Pts | Deliverable | Where | Status |
|---|--:|---|---|---|
| 1 | 1 | 1-sentence problem (no solution) | [§1.1](./SUBMISSION.md#11-the-problem-one-sentence) | 🔨 |
| 1 | 3 | Why it's a problem (who / what / today / gap) | [§1.2](./SUBMISSION.md#12-why-this-is-a-problem) | 🔨 |
| 1 | 3 | Current-workflow diagram | [§1.3](./SUBMISSION.md#13-how-the-user-solves-this-today) | 🔨 |
| 1 | 2 | Eval questions / input-output pairs | [§1.4](./SUBMISSION.md#14-questions-we-evaluate-against) | 🔨 |
| 2 | 1 | Solution in one sentence | [§2.1](./SUBMISSION.md#21-the-solution-one-sentence) | 🔨 |
| 2 | 7 | Infra diagram + one-line why per component | [§2.2](./SUBMISSION.md#22-infrastructure) | 🔨 |
| 2 | 7 | Agent-workflow diagram + 1-2 paragraphs | [§2.3](./SUBMISSION.md#23-agent-workflow) | 🔨 |
| 3 | 5 | All data sources + external APIs + their use | [§3.2](./SUBMISSION.md#32-data-sources-and-external-apis) | ✅ |
| 3 | 5 | Default chunking strategy + why | [§3.1](./SUBMISSION.md#31-chunking-strategy) | ✅ |
| 4 | 15 | End-to-end prototype + deploy with a front end | [§4](./SUBMISSION.md#task-4-end-to-end-agentic-rag-prototype) | 🔨 |
| 5 | 2 | Test dataset | [§5.1](./SUBMISSION.md#51-test-dataset) | ✅ |
| 5 | 10 | Evaluation harness | [§5.2](./SUBMISSION.md#52-evaluation-harness) | ✅ |
| 5 | 3 | Conclusions on performance | [§5.3](./SUBMISSION.md#53-conclusions) | ✅ |
| 6 | 6 | Advanced retriever + why | [§6.1](./SUBMISSION.md#61-advanced-retriever-cross-encoder-reranker) | ✅ |
| 6 | 2 | Before/after comparison table | [§6.2](./SUBMISSION.md#62-beforeafter-results) | ✅ |
| 6 | 6 | One other improvement + eval evidence | [§6.3](./SUBMISSION.md#63-second-improvement-hybrid-bm25--dense) | ✅ |
| 7 | 2 | Keep/change reflection for Demo Day | [§7](./SUBMISSION.md#task-7-next-steps) | ☐ |
| Final | 10 | 10-min-or-less Loom video (live demo + use case) | [SUBMISSION.md top](./SUBMISSION.md) | ☐ |
| Final | 10 | Written document answering every deliverable | [SUBMISSION.md](./SUBMISSION.md) | 🔨 |
| Final | 0 | All relevant code | the repository | 🔨 |

> Status so far: the CAS store, the 28-brief RAG corpus, the Chroma index, the **working LangGraph agent** (four tools + memory, through OpenRouter), the **Streamlit chat UI**, and the **evaluation harness** (gold set + LLM-judge + RAGAS + retrieval before/after tables) are **built**. Tasks 1-3, 5, 6 are answered in SUBMISSION.md with recorded numbers. Task 4's front end is done; only the one-time public deploy (a Community Cloud login) remains. Task 7 (next-steps reflection) and the final video/repo items remain.

## Cross-cutting requirements

Not separate rubric lines, but required across the build (mostly folded into Task 4). Missing any of these puts scored tasks at risk.

- **LLM gateway** (OpenRouter): done (`src/label_lens/llm.py`; the agent routes through it via `agent/graph.py`).
- **Own data for RAG**: done (the 28 per-additive briefs in `data/briefs/`, embedded into Chroma).
- **External API / agentic search**: done (openFDA recalls + Federal Register bans, `agent/live.py`).
- **Memory component**: done (user diet/allergy profile + product log, `agent/memory.py`).
- **Runs in a phone and laptop browser**: done (Streamlit chat UI, `streamlit_app.py`; responsive by default).
- **Front end + public deployment**: front end done; public deploy packaged and pending a one-time Community Cloud login (runbook in SUBMISSION §4.2). Explicitly required by Task 4.

## Where the points are (prioritise these)

Four areas hold **71 of 100** points: the prototype+deploy (15), the eval harness (10), and the two Final items (video 10, written doc 10), plus the two Task 2 diagrams (7+7) and the two Task 6 improvements (6+6). Everything else is small by comparison, so the schedule should protect time for the prototype, the eval harness, the diagrams, and the video/writeup above polishing the low-point prose.
