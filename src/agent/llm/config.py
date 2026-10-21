"""LLM seam configuration (mirrors the embeddings pluggable-seam pattern).

Providers:
- `ollama` (default) → ChatOllama against the local server
  (model default glm-5.3-flash:cloud, env-overridable) — no I/O at
  construction; calls happen at invoke time in real runtime use.
- `stub` → the deterministic stub components (offline tests / demos).

Tests never make live model calls (tester rule)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping, Optional

from agent.llm.classify import LLMClassifier, StubClassifier
from agent.llm.summarize import LLMSummarizer, StubSummarizer

DEFAULT_PROVIDER = "ollama"
DEFAULT_OLLAMA_MODEL = "glm-5.3-flash:cloud"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"


@dataclass(frozen=True)
class LLMConfig:
    """Which chat model classifies/summarizes in this process."""

    provider: str           # 'ollama' | 'stub'
    model: Optional[str] = None
    base_url: Optional[str] = None

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "LLMConfig":
        env = os.environ if env is None else env
        provider = (env.get("ADVISOR_LLM_PROVIDER") or DEFAULT_PROVIDER).strip().lower()
        if provider == "ollama":
            return cls(
                provider="ollama",
                model=(env.get("ADVISOR_LLM_MODEL") or DEFAULT_OLLAMA_MODEL).strip(),
                base_url=(env.get("ADVISOR_LLM_BASE_URL") or DEFAULT_OLLAMA_BASE_URL).strip(),
            )
        if provider == "stub":
            return cls(provider="stub")
        raise ValueError(
            f"Unknown ADVISOR_LLM_PROVIDER {provider!r}: use 'ollama' or 'stub'")


def get_llm(config: LLMConfig):
    """The chat model, or None in the stub configuration (no I/O offline)."""
    if config.provider == "stub":
        return None
    if config.provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(model=config.model, base_url=config.base_url,
                          temperature=0.0)
    raise ValueError(f"Unknown provider {config.provider!r}")  # unreachable via from_env


def get_classifier(config: LLMConfig):
    if config.provider == "stub":
        return StubClassifier()
    return LLMClassifier(get_llm(config))


def get_summarizer(config: LLMConfig):
    if config.provider == "stub":
        return StubSummarizer()
    return LLMSummarizer(get_llm(config))