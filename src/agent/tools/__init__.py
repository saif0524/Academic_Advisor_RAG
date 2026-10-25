"""The advisor agent's tools. Each layer builds on the one before it:

    LookupTools   (lookups.py)      read-only SQLite + Chroma lookups (FC33)
    EngineTools   (engine_tools.py) audits, recommendations, plan generation via core (FC24, FC29–FC32, FC2)
    ActionTools   (actions.py)      confirm-before-acting changes for the student (FC23)
    AdvisorToolkit (here)           + chat-session helpers; the one object graph nodes use
"""
from typing import List

from agent.tools.actions import ActionTools


class AdvisorToolkit(ActionTools):

    def ensure_chat_session(self, student_id: str) -> str:
        """Continue the student's latest chat session or start one (FC27/FC34)."""
        return self._sql.ensure_chat_session(student_id)

    def recent_history(self, student_id: str, session_id: str,
                       max_chars: int = 320) -> List[str]:
        """Last 12 turns, trimmed, as context for the LLM (FC27). Raises
        RecordNotFoundError for an unknown session (→ HTTP 404)."""
        rows = self._sql.get_chat_history(student_id, session_id)
        # Long turns keep head AND tail: an advisor's closing offer ("want me
        # to walk you through it?") is what a bare "yes please" answers (FC42).
        return [f"{row['role']}: {_trim(str(row['content']), max_chars)}" for row in rows[-12:]]


def _trim(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    head = max_chars // 3
    return text[:head] + " … " + text[-(max_chars - head):]
