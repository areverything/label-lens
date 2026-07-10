"""Thin OpenRouter (LLM gateway) client.

All model calls route through OpenRouter, per the certification requirement.
Config comes from .env.local:
  OPENROUTER_API_KEY   (required to make a call)
  OPENROUTER_MODEL     (optional; default below; swappable without code changes)
  OPENROUTER_BASE_URL  (optional)
"""
from __future__ import annotations

import os

import httpx
from dotenv import load_dotenv

from label_lens.config import ROOT

load_dotenv(ROOT / ".env.local")

BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")


class LLMNotConfigured(RuntimeError):
    """Raised when OPENROUTER_API_KEY is missing."""


def is_configured() -> bool:
    return bool(os.getenv("OPENROUTER_API_KEY"))


def chat(messages: list[dict], *, model: str | None = None,
         temperature: float = 0.2, max_tokens: int = 1200) -> str:
    """Send a chat completion through the gateway and return the text."""
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise LLMNotConfigured(
            "Set OPENROUTER_API_KEY in .env.local to call the LLM gateway."
        )
    r = httpx.post(
        f"{BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": model or DEFAULT_MODEL, "messages": messages,
              "temperature": temperature, "max_tokens": max_tokens},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()
