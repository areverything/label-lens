# Certification Challenge Rubric and Scorecard

The official grading rubric this submission is scored against, ingested verbatim, plus a task-level scorecard of how we're tracking. **100 points total.** (Course guidance: 85+ passes; below that you're asked to revise up, not failed.)

This doc is the **points reference and the scoring dashboard**. Deliverable-level status and the exact place each answer lives are tracked in the [coverage checklist in SUBMISSION.md](./SUBMISSION.md#coverage-checklist). Keep the two in sync: the checklist owns per-deliverable status, this doc owns the points and the task-level view.

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

## Scorecard (task-level tracking)

`done` = built and verified · `drafted` = written, will finalise · `not started`.

| Task | Max | Status | Note |
|---|--:|---|---|
| 1 | 9 | drafted | Problem, why, current-workflow diagram, eval questions all written in SUBMISSION; refine to Arnaud's voice. |
| 2 | 15 | drafted | Infra diagram + per-component why and the agent-workflow diagram are in SUBMISSION; will re-confirm once the app is built. |
| 3 | 10 | in progress | Chunking documented; the 28-brief RAG corpus is built. Still to do: enumerate **all** data sources + external APIs in one place. |
| 4 | 15 | not started | Needs the LangGraph agent, a Streamlit front end, and a public deployment. Highest single-task weight. |
| 5 | 15 | not started | The eval harness alone is 10 points, the biggest single deliverable. |
| 6 | 14 | not started | Reranker (6) + one other change (6) + comparison table (2), each measured. |
| 7 | 2 | not started | Short keep/change reflection. |
| Final | 20 | in progress | Written doc (10) is this repo's SUBMISSION.md, in progress; video (10) not started; code (0) accumulating. |

## Cross-cutting requirements

Not separate rubric lines, but required across the build (mostly folded into Task 4). Missing any of these puts scored tasks at risk.

- **LLM gateway** (OpenRouter): done (`src/label_lens/llm.py`).
- **Own data for RAG**: done (the 28 per-additive briefs in `data/briefs/`).
- **External API / agentic search**: planned (openFDA recalls + Federal Register bans).
- **Memory component**: planned (user diet/allergy profile + product log, Milestone 2).
- **Runs in a phone and laptop browser**: planned (Streamlit, Milestone 3).
- **Front end + public deployment**: planned (Streamlit Community Cloud, Milestone 3). Explicitly required by Task 4.

## Where the points are (prioritise these)

Four areas hold **71 of 100** points: the prototype+deploy (15), the eval harness (10), and the two Final items (video 10, written doc 10), plus the two Task 2 diagrams (7+7) and the two Task 6 improvements (6+6). Everything else is small by comparison, so the schedule should protect time for the prototype, the eval harness, the diagrams, and the video/writeup above polishing the low-point prose.
