"""Answer generation from tool payloads (§3 — the LLM interprets and
summarizes; it never decides). Both paths receive exactly the deterministic
payload; empty tool results stay empty in the wording."""
from __future__ import annotations

import json


class LLMSummarizer:
    """LLM wording FROM the payload only — the model never decides. On any
    model failure the turn degrades to the deterministic payload rendering
    (same tool data, templated wording — never fabricated, never silent)."""

    def __init__(self, llm) -> None:
        import logging

        from agent.llm.prompts import SUMMARIZE_SYSTEM

        self._model = llm
        self._system = SUMMARIZE_SYSTEM
        self._log = logging.getLogger("agent.summarize")

    def summarize(self, intent: str, payload: dict, user_input: str = "") -> str:
        from langchain_core.messages import HumanMessage, SystemMessage

        body = json.dumps({
            "intent": intent, "payload": payload, "user_question": user_input,
        })
        try:
            message = self._model.invoke([
                SystemMessage(content=self._system),
                HumanMessage(content=body),
            ])
        except Exception as exc:
            self._log.warning("LLM summarize unavailable (%s) — deterministic rendering", exc)
            return StubSummarizer().summarize(intent, payload, user_input)
        text = getattr(message, "text", None)
        if callable(text):  # BaseMessage.text is a method across versions
            text = text()
        if not text:
            content = getattr(message, "content", "")
            text = content if isinstance(content, str) else str(content)
        return str(text).strip() or "I couldn't generate a grounded answer — try again."


class StubSummarizer:
    """Deterministic, payload-grounded rendering (offline runs, tests, demos)."""

    def summarize(self, intent: str, payload: dict, user_input: str = "") -> str:
        handler = getattr(self, f"_render_{intent}", None)
        if handler is None:
            return "I can answer questions about your degree, classes, sections, and records."
        return handler(payload, user_input)

    # ------------------------------------------------------------ intents

    def _render_exact(self, payload: dict, user_input: str) -> str:
        course = payload.get("found_course")
        lines: list = []
        for miss in payload.get("misses") or []:
            lines.append(
                f"I don't have {miss} in the catalog on record — double-check the course code.")
        if course is not None:
            hours = (f"{course['credit_hours']} credit hours"
                     if course.get("credit_hours") else "no credit hours on record")
            lines.append(f"{course['course_id']} — {course['title']} ({hours}).")
            if course.get("description"):
                lines.append(str(course["description"]))
            sections = payload.get("sections") or []
            if sections:
                rendered = [
                    f"{s['section_id']}: {s.get('instructor') or 'TBA'}"
                    f" — {s.get('schedule_string') or 'schedule TBD'}"
                    for s in sections
                ]
                lines.append("Sections: " + "; ".join(rendered))
            else:
                lines.append("No sections on record for this course.")
        elif payload.get("profile"):
            profile = payload["profile"]
            major = profile.get("current_major") or "no major set"
            degree = profile.get("selected_degree_id") or "no degree tracked"
            lines.append(f"Profile for {profile.get('name') or 'you'} — major: {major}; tracked degree: {degree}.")
            classes = payload.get("classes") or []
            if classes:
                lines.append("On your profile: " + ", ".join(
                    f"{c['course_id']} ({c['status']})" for c in classes))
        elif not payload.get("misses"):
            lines.append(
                "I couldn't find that on record — try a course code or ask about your classes.")
        return " ".join(lines)

    def _render_semantic(self, payload: dict, user_input: str) -> str:
        catalog_hits = payload.get("catalog_hits") or []
        hits = payload.get("hits") or []
        if not hits and not catalog_hits:
            query = payload.get("query") or user_input
            return (
                f"I couldn't find anything about “{query}” in the catalog corpus — "
                "try a course code or another phrasing.")
        lines = ["Closest matches in the course catalog:"]
        for course in hits:
            hours = f" ({course['credit_hours']} hrs)" if course.get("credit_hours") else ""
            snippet = (course.get("description") or "")[:160]
            lines.append(f"• {course['course_id']} — {course['title']}{hours}. {snippet}")
        for hit in catalog_hits:
            label = hit.get("source") or "catalog"
            text = (hit.get("text") or "")[:220]
            lines.append(f"• {label} ({hit.get('kind')}): {text}…")
        return "\n".join(lines)

    def _render_recommend(self, payload: dict, user_input: str) -> str:
        candidates = payload.get("candidates") or []
        if not candidates:
            return ("I couldn't build a candidate list — no matching courses and no "
                    "selected degree on record.")
        eligible = [c for c in candidates if c["eligible"] is True]
        unknown = [c for c in candidates if c["eligible"] is None]
        blocked = [c for c in candidates if c["eligible"] is False]
        lines: list = []
        if eligible:
            lines.append("Eligible after the deterministic checks (FC29–FC32): " + ", ".join(
                f"{c['course_id']} — {c['title']}" for c in eligible) + ".")
        for course in unknown:
            unknown_reason = next(
                (chk["reason"] for chk in course["checks"] if chk["passed"] is None),
                "data missing")
            lines.append(f"Can't verify yet — {course['course_id']}: {unknown_reason}")
        for course in blocked:
            lines.append(f"Not eligible — {course['course_id']}: {course['reason']}")
        return "\n".join(lines)

    def _render_audit(self, payload: dict, user_input: str) -> str:
        if payload.get("progress") is not None:
            progress = payload["progress"]
            percent = (f"{progress['completion_percent']:g}% complete"
                       if progress.get("completion_percent") is not None
                       else "no completion data on record")
            lines = [f"Progress toward {progress['degree_id']}: {percent}."]
            for line in progress.get("outstanding_requirements") or []:
                lines.append(f"• {line}")
            if payload.get("misses"):
                lines.append(f"(not found: {', '.join(payload['misses'])})")
            return "\n".join(lines)
        course = payload.get("course")
        result = payload.get("result")
        if course is None or result is None:
            misses = payload.get("misses") or []
            if misses:
                return (f"I don't have {', '.join(misses)} on record to audit — eligibility "
                        "audits need a real course code.")
            return "An eligibility audit needs a course code — e.g. “Can I take CSE 4308?”"
        if result["eligible"] is True:
            lines = [f"Good news — you're eligible for {course['course_id']} "
                     f"({course['title']}) per the deterministic checks."]
        elif result["eligible"] is False:
            lines = [f"Not eligible for {course['course_id']} right now."]
        else:
            lines = [f"I can't fully evaluate {course['course_id']} with the data on record."]
        for check in result.get("checks") or []:
            state = {True: "pass", False: "FAIL", None: "unknown"}[check["passed"]]
            lines.append(f"• {check['check_id']}: {state} — {check.get('reason') or ''}")
        return "\n".join(lines)

    def _render_propose_action(self, payload: dict, user_input: str) -> str:
        refusal = payload.get("refusal")
        if refusal:
            return refusal
        proposed = payload.get("proposed")
        if proposed:
            return (f"Please confirm from the card: {proposed['description']}. "
                    "Nothing has been changed yet — I only act after your confirmation (FC23).")
        return "I couldn't prepare that action."

    def _render_plan_generation(self, payload: dict, user_input: str) -> str:
        refusal = payload.get("refusal")
        if refusal:
            return refusal
        plan = payload.get("plan")
        if not plan or not plan.get("semesters"):
            return ("I couldn't build a plan from the data on record — nothing "
                    "was invented.")
        semesters = plan["semesters"]
        first, last = semesters[0], semesters[-1]
        lines = [
            f"Here's a semester-by-semester plan for {plan['target_major']}"
            + (f" — {plan['concentration']}" if plan.get("concentration") else "")
            + f", covering {first['term']} {first['year']} through "
            f"{last['term']} {last['year']} ({len(semesters)} semesters, "
            f"{'summer sessions included' if plan.get('includes_summer') else 'no summer sessions'})."
        ]
        for note in payload.get("notes") or []:
            lines.append(f"• {note}")
        lines.append("Review it in the planner, edit what you need, then make it "
                     "active when it looks right.")
        return "\n".join(lines)

    def _render_confirm(self, payload: dict, user_input: str) -> str:
        if payload.get("error"):
            return payload["error"]
        if payload.get("decision") == "cancelled":
            return payload.get("outcome") or "Cancelled — no changes were made."
        return payload.get("outcome") or "Done."

    def _render_clarify(self, payload: dict, user_input: str) -> str:
        return payload.get("followup") or \
            "Could you tell me a bit more about what you'd like to do?"

    def _render_chitchat(self, payload: dict, user_input: str) -> str:
        return ("Happy to help. I can answer questions about degrees, requirements, classes, "
                "sections, professors, and your progress — grounded in your records and the "
                "course catalog.")