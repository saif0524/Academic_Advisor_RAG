"""§3 advisor graph (LangGraph) — classify → route → tools → summarize.

Rules (langgraph skill): nodes decide routes and delegate; ALL constraint
math lives in `core` behind the toolkit — the graph cannot bypass the
validator (FC29–FC32) or generate plans. FC23 proposals persist in SQL and
execute only on the next, explicitly-confirmed turn (durable pause/resume
across HTTP requests; documented in the domain model).

State: `AdvisorState`. Durable conversation state is SQLite (FC34; each turn
is a fresh invocation with history loaded from SQL through the toolkit),
which is why no checkpointer is installed — divergence from the skill's dev
MemorySaver default, documented in the domain-model notes."""
from __future__ import annotations

from typing import Annotated, Dict, List, Optional, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


class AdvisorState(TypedDict, total=False):
    """One advising turn; nodes return partial updates (never mutate)."""

    messages: Annotated[List[AnyMessage], add_messages]
    history: List[str]                # FC27: prior turns from SQLite (FC34)
    user_input: str
    student_id: str
    session_id: Optional[str]
    confirmed_action_id: Optional[str]   # FC23: explicit confirmation resume
    cancelled_action_id: Optional[str]   # FC23: explicit cancellation
    intent: str
    params: Dict
    followup: Optional[str]
    tool_payload: Dict
    pending_action: Optional[Dict]
    reply: str


INTENT_ROUTES: Dict[str, str] = {
    # Explicit routing map — named route functions read only state fields.
    "exact": "exact_tools",
    "semantic": "semantic_tools",
    "recommend": "recommend_tools",
    "audit": "audit_tools",
    "propose_action": "propose_action",
    "plan_generation": "plan_tools",
    "chitchat": "summarize",
}


def _student_context(toolkit, student_id: str) -> dict:
    """FC27: routing hints for the classifier (never a source of facts)."""
    profile = toolkit.student_profile(student_id)
    return {
        "student_id": student_id,
        "major": getattr(profile, "current_major", None),
        "has_active_plan": toolkit.active_plan(student_id) is not None,
    }


def build_advisor_graph(toolkit, classifier, summarizer):
    """Build the advisor StateGraph over the injected toolkit + LLM parts."""

    # ------------------------------------------------------------- nodes

    def entry_gate(state: AdvisorState) -> dict:
        return {}  # pure router: classify or resume a pending decision (FC23)

    def classify_node(state: AdvisorState) -> dict:
        """§3 classify_query_intent (FC22/FC27/FC33) — LLM (or stub) classifies;
        context = recent history from SQL (loaded via toolkit)."""
        history = toolkit.recent_history(state["student_id"], state.get("session_id")) \
            if state.get("session_id") else []
        classification = classifier.classify(
            state["user_input"],
            history=history,
            student_context=_student_context(toolkit, state["student_id"]),
        )
        return {
            "history": history,
            "intent": classification.intent,
            "params": dict(classification.params),
            "followup": classification.followup,
            "messages": [HumanMessage(content=state["user_input"])],
        }

    def exact_tools_node(state: AdvisorState) -> dict:
        """SQLite facts (FC8/FC11/FC12 + profile/plan reads) — misses stay
        misses; nothing is ever backfilled."""
        params = state.get("params") or {}
        mentions = params.get("course_mentions") or []
        payload: Dict = {
            "queried": state["user_input"], "found_course": None,
            "misses": [], "sections": [], "profile": None, "classes": [],
        }
        for mention in mentions[:1]:  # the primary course mention
            course = toolkit.find_course(mention)
            if course is None:
                payload["misses"].append(mention)
                continue
            payload["found_course"] = {
                "course_id": course.course_id,
                "title": course.title,
                "credit_hours": course.credit_hours,
                "description": course.description,
                "department": course.department,
                "prerequisites": course.prerequisites,
                "corequisites": course.corequisites,
                "offered_terms": course.offered_terms,
            }
            payload["sections"] = [
                {
                    "section_id": s.section_id,
                    "term": s.semester_term,
                    "instructor": s.instructor,
                    "schedule_string": s.get_schedule_string(),
                    "open_seats": s.has_open_seats(),
                }
                for s in toolkit.sections(course.course_id)
            ]
        if not mentions and params.get("topic") == "plan":
            # FC22/FC27: the ACTIVE plan (FC6), SQLite only (FC33); None → honest "no plan".
            payload["plan"] = toolkit.plan_context(state["student_id"])
        elif not mentions:
            student = toolkit.student_profile(state["student_id"])
            if student is not None:
                payload["profile"] = {
                    "name": student.name, "current_major": student.current_major,
                    "concentration": student.concentration,
                    "selected_degree_id": student.selected_degree_id,
                }
                payload["classes"] = [
                    {"course_id": r.course_id, "status": r.status,
                     "grade": r.grade, "semester_taken": r.semester_taken}
                    for r in toolkit.student_classes(state["student_id"])
                ]
        return {"tool_payload": payload}

    def semantic_tools_node(state: AdvisorState) -> dict:
        """Chroma facts (FC9/FC22) — course corpus first, catalog text on a miss."""
        params = state.get("params") or {}
        query = params.get("query") or state["user_input"]
        payload: Dict = {"query": query, "hits": toolkit.semantic_courses(query, k=6),
                         "catalog_hits": []}
        if not payload["hits"]:
            payload["catalog_hits"] = toolkit.catalog_search(query, k=3)
        return {"tool_payload": payload}

    def recommend_tools_node(state: AdvisorState) -> dict:
        """FC22 suggestions — every candidate validated by the engine
        (FC29–FC32) inside `recommend_candidates`."""
        params = state.get("params") or {}
        plan = toolkit.active_plan(state["student_id"])
        planned = {cid for sem in (plan or {}).get("semesters", [])
                   for cid in sem.get("courses", [])}
        result = toolkit.recommend_candidates(
            state["student_id"], params.get("query"), k=6, exclude_ids=sorted(planned))
        return {"tool_payload": result}

    def audit_tools_node(state: AdvisorState) -> dict:
        """FC24 — course eligibility (validator) or degree progress (FC19)."""
        params = state.get("params") or {}
        mentions = params.get("course_mentions") or []
        if mentions:
            audit = toolkit.course_audit(state["student_id"], mentions[0])
            if audit is None:
                return {"tool_payload": {"course": None, "result": None,
                                         "progress": None, "misses": mentions}}
            return {"tool_payload": {"course": audit["course"], "result": audit["result"],
                                     "progress": None}}
        progress = toolkit.degree_audit(state["student_id"], None)
        return {"tool_payload": {"course": None, "result": None, "progress": progress,
                                 "plan": toolkit.plan_context(state["student_id"])}}

    def plan_tools_node(state: AdvisorState) -> dict:
        """FC2/FC25 — plan generation runs through the deterministic engine
        (DegreePlanGenerator); this node only assembles inputs and persists
        the built plan. It can never bypass the validator or invent courses."""
        params = dict(state.get("params") or {})
        return {"tool_payload": toolkit.generate_plan(state["student_id"], params)}

    def propose_action_node(state: AdvisorState) -> dict:
        """FC23 — deterministic prechecks, then persist the proposal. The
        profile is untouched until the confirming turn executes it."""
        params = dict(state.get("params") or {})
        params.pop("followup", None)
        session_id = state.get("session_id") or toolkit.ensure_chat_session(
            state["student_id"])
        outcome = toolkit.propose_action(
            state["student_id"], session_id, params.get("action_type", ""), params)
        return {
            "tool_payload": outcome,
            "pending_action": outcome.get("proposed"),
            "session_id": session_id,
        }

    def clarify_node(state: AdvisorState) -> dict:
        """FC28 bounded clarification: exactly one question, then END. The loop
        lives across user turns (history), never inside the graph run."""
        question = state.get("followup") or \
            "Could you tell me a bit more about what you'd like to do?"
        return {"reply": question, "pending_action": None}

    def confirm_node(state: AdvisorState) -> dict:
        """FC23 — resume ONLY on the explicit decision carried from the client:
        gate recheck (ownership/session/open) → deterministic execution."""
        confirmed = state.get("confirmed_action_id")
        cancelled = state.get("cancelled_action_id")
        decision = "confirmed" if confirmed else "cancelled"
        row = toolkit.check_decision(
            confirmed or cancelled or "", state["student_id"], state.get("session_id"))
        if row is None:
            return {"intent": "confirm", "pending_action": None,
                    "tool_payload": {"decision": decision, "outcome": None,
                                     "error": toolkit.decision_error()}}
        result = toolkit.resolve_decision(row, decision)
        return {
            "intent": "confirm",
            "pending_action": None,
            "tool_payload": {"decision": decision,
                             "outcome": result["outcome"],
                             "error": result["error"]},
        }

    def summarize_node(state: AdvisorState) -> dict:
        """§3 summarize — words the payload; never invents (grounded rule)."""
        reply = summarizer.summarize(
            state.get("intent") or "chitchat",
            state.get("tool_payload") or {},
            state.get("user_input") or "",
        )
        return {"reply": reply, "messages": [AIMessage(content=reply)]}

    # ------------------------------------------------------------ routing

    def route_entry(state: AdvisorState) -> str:
        if state.get("confirmed_action_id") or state.get("cancelled_action_id"):
            return "confirm"  # FC23 resume — classifying would re-propose
        return "classify"

    def route_after_classify(state: AdvisorState) -> str:
        if state.get("followup"):
            return "clarify"  # FC28: under-specified request → one question
        return INTENT_ROUTES.get(state.get("intent") or "", "summarize")

    # ------------------------------------------------------------ assembly

    graph = StateGraph(AdvisorState)
    graph.add_node("entry_gate", entry_gate)
    graph.add_node("classify", classify_node)
    graph.add_node("exact_tools", exact_tools_node)
    graph.add_node("semantic_tools", semantic_tools_node)
    graph.add_node("recommend_tools", recommend_tools_node)
    graph.add_node("audit_tools", audit_tools_node)
    graph.add_node("plan_tools", plan_tools_node)
    graph.add_node("propose_action", propose_action_node)
    graph.add_node("clarify", clarify_node)
    graph.add_node("confirm", confirm_node)
    graph.add_node("summarize", summarize_node)

    graph.add_edge(START, "entry_gate")
    graph.add_conditional_edges("entry_gate", route_entry,
                                {"confirm": "confirm", "classify": "classify"})
    graph.add_conditional_edges("classify", route_after_classify, {
        # identity map over every possible route output (explicit per skill)
        "exact_tools": "exact_tools",
        "semantic_tools": "semantic_tools",
        "recommend_tools": "recommend_tools",
        "audit_tools": "audit_tools",
        "propose_action": "propose_action",
        "plan_tools": "plan_tools",
        "clarify": "clarify",
        "summarize": "summarize",
    })
    for node in ("exact_tools", "semantic_tools", "recommend_tools", "audit_tools",
                 "propose_action", "plan_tools", "confirm"):
        graph.add_edge(node, "summarize")
    graph.add_edge("summarize", END)
    graph.add_edge("clarify", END)
    return graph.compile()