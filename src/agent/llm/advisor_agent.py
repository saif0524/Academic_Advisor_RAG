"""§3 AIAdvisorAgent — the conversation entry point (FC22–FC24, FC27–FC28).

One turn: history from SQL (FC34) → graph invoke → {reply, pending_action}.
The chat service owns message persistence; this class owns classification,
routing, deterministic tool dispatch, and the FC23 gate."""
from __future__ import annotations

from typing import Optional

from agent.llm.config import LLMConfig, get_classifier, get_summarizer
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
            summarizer=get_summarizer(config))
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
            {
                "messages": [],
                "user_input": user_input,
                "student_id": student_id,
                "session_id": session_id,
                "confirmed_action_id": confirmed_action_id,
                "cancelled_action_id": cancelled_action_id,
                "history": [],
            },
            config={"recursion_limit": 25},
        )
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