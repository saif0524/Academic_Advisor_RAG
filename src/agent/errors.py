"""Agent-zone exceptions.

`LLMError` maps to HTTP 503 `llm_unavailable` (server/errors.py) — the model
being down must never fabricate an advising answer. In-band failures
(unknown actions, refusals) travel as data in tool payloads instead, so the
assistant can answer honestly without an error status."""
from __future__ import annotations


class LLMError(Exception):
    """LLM provider unreachable or generation failed (never live in tests)."""


class PendingActionError(Exception):
    """A decision id or action row is unknown, not open, or not owned by the
    caller — defensive double-check behind the FC23 confirmation gate."""