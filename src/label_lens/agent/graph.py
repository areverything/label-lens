"""The LangGraph agent: route a question to the right lane and compose a cited answer.

A ReAct agent over the four tools, with the user's memory folded into the system
prompt so it can personalise and answer cumulative questions. Every model call
goes through the OpenRouter gateway. LangSmith tracing turns on automatically
when a LangSmith key is present.
"""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from label_lens.agent import memory
from label_lens.agent.tools import ALL_TOOLS, _con
from label_lens.agent.trace import summarize_run
from label_lens.config import ROOT

load_dotenv(ROOT / ".env.local")

BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

SYSTEM_RULES = """You are Label Lens, an assistant that explains food-additive \
regulatory status and evidence to shoppers.

Use the tools to ground every answer; do not answer from memory:
- additive_status: a jurisdiction's legal status (banned/permitted/...). Exact facts.
- search_briefs: evidence and the "why" behind a status. Explanation.
- check_recalls: live openFDA recalls for a product or additive.
- recent_regulatory_actions: live Federal Register FDA rules and revocations.

Hard rules:
1. Cite. Every legal claim names its regulation/citation; every evidence claim \
comes from a retrieved brief passage. If a tool returns nothing, say so plainly.
2. Keep three things separate and never conflate them: LEGAL STATUS (a regulator's \
decision), HAZARD CLASSIFICATION (e.g. an IARC cancer-hazard group), and PERSONAL \
HARM. "Banned somewhere" does not mean "proven harmful".
3. Safety boundary: if asked whether something will hurt the user (a health \
verdict), give the regulatory status and the evidence, then decline to give \
medical advice and suggest a professional. You are not a doctor.
4. Be concise and plain-language."""


def _setup_tracing() -> None:
    if os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY"):
        os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
        os.environ.setdefault("LANGCHAIN_PROJECT", "label-lens")


_setup_tracing()


@lru_cache(maxsize=1)
def _model() -> ChatOpenAI:
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Set OPENROUTER_API_KEY in .env.local to run the agent.")
    return ChatOpenAI(model=DEFAULT_MODEL, base_url=BASE_URL, api_key=key,
                      temperature=0.2)


def _memory_block(user_id: str) -> str:
    con = _con()
    profile = memory.get_profile(con, user_id)
    log = memory.get_log_with_additives(con, user_id)
    if not profile and not log:
        return ""
    parts = ["\n\nUser memory (use it to personalise, still cite facts). The "
             "additives below are from the store, not a guess: treat them as the "
             "authoritative ingredient list and do not invent others."]
    if profile:
        parts.append(f"- Profile: diet={profile['diet'] or 'none'}, "
                     f"allergies={profile['allergies'] or 'none'}")
    for r in log:
        # Strip the "en:" tag prefix to the bare E-numbers for the model.
        codes = ", ".join(t.split(":")[-1].upper() for t in r["additives"].split(",") if t)
        line = f"- Logged: {r['name'] or r['barcode']}"
        line += f" — additives: {codes}" if codes else " — additives: (not on file)"
        parts.append(line)
    return "\n".join(parts)


def answer_with_trace(question: str, *, user_id: str = "demo") -> tuple[str, list[dict]]:
    """Answer one question and return (reply, activity trace).

    The trace is the ordered list of steps the agent actually took (which lane,
    the query, a one-line result, and the requirement each step demonstrates),
    for the UI to show as a background activity log.
    """
    agent = create_react_agent(
        _model(), ALL_TOOLS, prompt=SYSTEM_RULES + _memory_block(user_id),
    )
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    messages = result["messages"]
    reply = messages[-1].content
    return reply, summarize_run(messages, reply)


def answer(question: str, *, user_id: str = "demo") -> str:
    """Answer one question for a user, reading their memory first."""
    reply, _ = answer_with_trace(question, user_id=user_id)
    return reply
