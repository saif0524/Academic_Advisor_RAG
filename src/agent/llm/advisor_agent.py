"""§3 AIAdvisorAgent — the conversation entry point (FC22–FC24, FC27–FC28).

One turn: history from SQL (FC34) → graph invoke → {reply, pending_action}.
The chat service owns message persistence; this class owns classification,
routing, deterministic tool dispatch, and the FC23 gate."""
from __future__ import annotations

from typing import Optional

from agent.llm.config import LLMConfig, get_classifier, get_explorer, get_summarizer
from agent.llm.graph import build_advisor_graph
from agent.tools import AdvisorToolkit


class AIAdvisorAgent:
    """Graph-backed advisor (§3); one instance per app process."""

    def __init__(self, graph, sql_db_manager) -> None:
        self._graph = graph
        self._sql = sql_db_manager

    @classmethod
    def build(cls, sql_db_manager, vector_db_manager, llm_config: Optional[LLMConfig] = None) -> "AIAdvisorAgent":
        config = llm_config or LLMConfig.from_env()
        toolkit = AdvisorToolkit(sql_db_manager, vector_db_manager)
        graph = build_advisor_graph(
            toolkit=toolkit, classifier=get_classifier(config),
            summarizer=get_summarizer(config), explorer=get_explorer(config))
        return cls(graph, sql_db_manager)

    # ------------------------------------------------------------ contract

    def process_query(
        self, student_id: str, user_input: str, session_id: Optional[str] = None,
        confirmed_action_id: Optional[str] = None,
        cancelled_action_id: Optional[str] = None,
    ) -> dict:
        """§3 main entry: one advising turn. Returns
        {reply, pending_action (FC23 proposal or None), session_id}."""
        result = self._graph.invoke(
            self._initial_state(student_id, user_input, session_id,
                                confirmed_action_id, cancelled_action_id),
            config={"recursion_limit": 25},
        )
        return self._turn_result(result, session_id)

    def process_query_stream(
        self, student_id: str, user_input: str, session_id: Optional[str] = None,
        confirmed_action_id: Optional[str] = None,
        cancelled_action_id: Optional[str] = None,
    ):
        """FC39: same turn as `process_query`, yielding events as they happen —
        `check` (deterministic validator results), `token` (answer text), then
        a final `done` {reply, pending_action, session_id}."""
        final: dict = {}
        for mode, data in self._graph.stream(
            self._initial_state(student_id, user_input, session_id,
                                confirmed_action_id, cancelled_action_id),
            config={"recursion_limit": 25},
            stream_mode=["custom", "values"],
        ):
            if mode == "custom":
                yield data
            else:
                final = data
        yield {"type": "done", **self._turn_result(final, session_id)}

    @staticmethod
    def _initial_state(student_id, user_input, session_id, confirmed_action_id,
                       cancelled_action_id) -> dict:
        return {
            "messages": [],
            "user_input": user_input,
            "student_id": student_id,
            "session_id": session_id,
            "confirmed_action_id": confirmed_action_id,
            "cancelled_action_id": cancelled_action_id,
            "history": [],
        }

    @staticmethod
    def _turn_result(result: dict, session_id: Optional[str]) -> dict:
        pending = result.get("pending_action")
        if pending is not None:
            pending = {
                "action_id": pending["action_id"],
                "action_type": pending["action_type"],
                "description": pending["description"],
            }
        return {
            "reply": result.get("reply") or "",
            "pending_action": pending,
            "session_id": result.get("session_id") or session_id,
        }