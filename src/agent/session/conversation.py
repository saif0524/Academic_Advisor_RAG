"""§3 ConversationSession — conversation state (FC27) over SQLite (FC34).

History is the durable multi-turn context: the graph classifier/summarizer
receive a trimmed window on every turn, so follow-ups like "What about next
semester?" keep their prior context without any in-process memory."""
from __future__ import annotations

from typing import Dict, List, Optional


class ConversationSession:
    """§3 conversation layer, §4-persisted (chat_sessions/chat_messages)."""

    MAX_HISTORY_TURNS = 12

    def __init__(self, sql_db_manager, student_id: str, session_id: Optional[str]) -> None:
        self._sql = sql_db_manager
        self.student_id = student_id
        self.session_id = session_id
        self.context_state: Dict = {}  # §3: temporary multi-turn slots (FC27)

    def load_raw_history(self) -> List[dict]:
        """FC34 turns for this session; unknown session id raises
        RecordNotFoundError (mapped to 404 by the HTTP layer)."""
        if not self.session_id:
            return []
        return self._sql.get_chat_history(self.student_id, self.session_id)

    def recent_history(self) -> List[str]:
        """Trimmed, oldest-first 'user:/assistant:' lines for prompts (FC27)."""
        rows = self.load_raw_history()
        trimmed = rows[-self.MAX_HISTORY_TURNS:]
        return [f"{row['role']}: {str(row['content'])[:220]}" for row in trimmed]

    def add_user_message(self, content: str) -> None:
        self._sql.append_chat_message(
            self._session_or_new(), self.student_id, "user", content)

    def add_ai_message(self, content: str) -> None:
        self._sql.append_chat_message(
            self._session_or_new(), self.student_id, "assistant", content)

    def update_context_state(self, key: str, value) -> None:
        """§3 hook (FC27 follow-up turns); durable state stays the history."""
        self.context_state[key] = value

    def _session_or_new(self) -> str:
        if not self.session_id:
            self.session_id = self._sql.ensure_chat_session(self.student_id)
        return self.session_id