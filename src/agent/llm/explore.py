"""FC42 explorers — answer open-ended / brainstorming questions.

`LLMExplorer` runs a bounded tool-calling loop (read-only tools from
`agent.tools.explore`, at most MAX_TOOL_CALLS per turn); its wording is
non-deterministic by design. `StubExplorer` is the deterministic stand-in
(offline tests/demos and the LLM path's degraded fallback). Neither can act
on the student's account, and the graph applies the deterministic answer
guard (`ground_answer`) to whatever they return."""
from __future__ import annotations

import logging
from typing import Callable, List, Optional

from agent.tools.explore import MAX_TOOL_CALLS, explore_tools

_log = logging.getLogger("agent.explore")

StepFn = Optional[Callable[[str], None]]


def _student_line(toolkit, student_id: str) -> str:
    student = toolkit.student_profile(student_id)
    if student is None:
        return "Student: no profile on record."
    return (f"Student: major={student.current_major or 'none'}, "
            f"concentration={student.concentration or 'none'}, "
            f"degree={student.selected_degree_id or 'none'}.")


def _text(message) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, list):  # some providers return content blocks
        content = "".join(part.get("text", "") if isinstance(part, dict) else str(part)
                          for part in content)
    return str(content or "").strip()


class LLMExplorer:
    def __init__(self, llm) -> None:
        self._model = llm

    def explore(self, toolkit, student_id: str, user_input: str,
                history: List[str], on_step: StepFn = None) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

        from agent.llm.prompts import EXPLORE_SYSTEM

        tools = explore_tools(toolkit, student_id, on_step)
        by_name = {t.name: t for t in tools}
        try:
            bound = self._model.bind_tools(tools)
            messages = [
                SystemMessage(content=EXPLORE_SYSTEM),
                HumanMessage(content="\n".join(
                    ["Recent conversation (oldest first):", *(history or ["(none)"]),
                     _student_line(toolkit, student_id), "", "Student's message:", user_input])),
            ]
            used = 0
            while True:
                reply = bound.invoke(messages)
                calls = getattr(reply, "tool_calls", None) or []
                if not calls:
                    return _text(reply) or StubExplorer().explore(
                        toolkit, student_id, user_input, history, on_step)
                messages.append(reply)
                for call in calls:
                    if used >= MAX_TOOL_CALLS:
                        break
                    tool = by_name.get(call.get("name"))
                    try:
                        content = tool.invoke(call.get("args") or {}) if tool else \
                            f"Unknown tool {call.get('name')!r}."
                    except Exception as exc:  # a bad tool arg is the model's problem, not a crash
                        content = f"Tool error: {exc}"
                    messages.append(ToolMessage(content=str(content), tool_call_id=call.get("id") or ""))
                    used += 1
                if used >= MAX_TOOL_CALLS:
                    # Budget spent (FC42): one last tool-less answer from the results so far.
                    final = self._model.invoke(messages + [HumanMessage(content=(
                        "Tool budget reached. Answer the student now using only the "
                        "tool results above; do not call more tools."))])
                    return _text(final) or StubExplorer().explore(
                        toolkit, student_id, user_input, history, on_step)
        except Exception as exc:
            _log.warning("LLM explore unavailable (%s) — deterministic exploration", exc)
            return StubExplorer().explore(toolkit, student_id, user_input, history, on_step)


class StubExplorer:
    """Deterministic exploration: programs on record + course matches."""

    def explore(self, toolkit, student_id: str, user_input: str,
                history: List[str], on_step: StepFn = None) -> str:
        from agent.llm.classify import is_followup_reply

        step = on_step or (lambda _text: None)
        query = user_input
        if is_followup_reply(user_input):  # "yes please" → search what was offered
            query = next((h.split(":", 1)[-1] for h in reversed(history or [])
                          if h.startswith("assistant:")), user_input)

        lines: List[str] = []
        programs = toolkit.list_programs()
        step("SQLite: listed degrees and concentrations")
        if programs:
            lines.append("**Programs on record**")
            for p in programs:
                tracks = ", ".join(p["concentrations"]) or "no concentrations"
                hours = f", {p['total_credits_required']} hrs" if p.get("total_credits_required") else ""
                lines.append(f"• {p['degree_id']} — {p['major_name']}{hours}. Concentrations: {tracks}.")

        hits = toolkit.semantic_courses(query, k=4)
        step("Chroma: semantic search over course descriptions")
        if hits:
            lines.append("")
            lines.append("**Courses related to your question**")
            for h in hits:
                lines.append(f"• {h['course_id']} — {h['title']}.")
        if not lines:
            return "I couldn't find any programs or courses on record to explore."
        lines.append("")
        lines.append("Each course above was run through the eligibility checks (FC29–FC32) — "
                     "see the work shown. Ask what a concentration requires, or "
                     "\"can I take …?\" about any course, to dig deeper.")
        return "\n".join(lines)
