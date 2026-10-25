"""Actions the assistant takes for the student — confirm before acting (FC23).

Two steps:
1. `propose_action` checks the request with deterministic code and stores it
   as an open row in `chat_pending_actions`. Nothing changes on the profile yet.
2. When the student clicks confirm/cancel, `check_decision` verifies the row
   belongs to them and is still open, then `resolve_decision` runs the change
   (confirmed) or just closes the row (cancelled).

Each action type has one `_propose_*` method and one `_do_*` method. Both
raise `Refusal` with a user-facing reason when the action can't go ahead.
"""
from __future__ import annotations

import json
import re
from typing import List, Optional, Tuple

from core.engine.generator import DegreePlanGenerator, semesters_payload
from database.sql.sqlite_manager import CLASS_STATUSES

from agent.tools.engine_tools import EngineTools

_TERM_RE = re.compile(r"(Fall|Spring|Summer)\s+(\d{4})", re.IGNORECASE)
_PLAN_EDITS = ("plan_add_course", "plan_remove_course", "plan_move_course")
# FC23: the confirmation card states the follow-on plan regeneration up front.
_REPLAN_NOTE = ", and generate a new active degree plan for it"


class Refusal(Exception):
    """The action can't go ahead; the message is shown to the student."""


class ActionTools(EngineTools):

    def __init__(self, sql_db_manager, vector_db_manager=None) -> None:
        super().__init__(sql_db_manager, vector_db_manager)
        self._decision_error: Optional[str] = None

    # ------------------------------------------------------- step 1: propose

    def propose_action(
        self, student_id: str, session_id: str, action_type: str, params: Optional[dict] = None,
    ) -> dict:
        """Precheck + store a pending action. Returns {"proposed", "refusal"}."""
        params = dict(params or {})
        try:
            if action_type in _PLAN_EDITS:
                _, _, description, payload = self._edit_active_plan(student_id, action_type, params)
            else:
                proposer = {
                    "add_class": self._propose_add_class,
                    "change_class_status": self._propose_change_class_status,
                    "change_major": self._propose_change_major,
                    "change_concentration": self._propose_change_concentration,
                    "change_degree": self._propose_change_degree,
                    "activate_plan": self._propose_activate_plan,
                }.get(action_type)
                if proposer is None:
                    raise Refusal(f"Unsupported action {action_type!r} on your behalf (FC23).")
                description, payload = proposer(student_id, params)
        except Refusal as refusal:
            return {"proposed": None, "refusal": str(refusal)}

        action_id = self._sql.create_pending_action(
            session_id, student_id, action_type, description, payload)
        return {"proposed": {
            "action_id": action_id,
            "session_id": session_id,
            "action_type": action_type,
            "description": description,
            "payload": json.dumps(payload),
            "status": "open",
        }, "refusal": None}

    def _propose_add_class(self, student_id: str, params: dict) -> Tuple[str, dict]:
        course = self.find_course(params.get("course_id", ""))
        if course is None:
            raise Refusal(f"There is no course on record for {params.get('course_id')!r} — nothing will be added.")
        records = self.student_classes(student_id)
        existing = next((r for r in records if r.course_id == course.course_id), None)
        if existing is not None and existing.status in {"passed", "taken"}:
            raise Refusal(f"{course.course_id} is already completed on your record (FC30) — it cannot be added again.")
        if existing is not None and existing.status == "in_progress":
            raise Refusal(f"{course.course_id} is already in progress this semester.")

        result = self._check_course(course, records, self.selected_degree(student_id))
        failed = [c for c in result["checks"] if c["passed"] is False and c["check_id"] in {"FC29", "FC30", "FC32"}]
        if failed:
            raise Refusal(" / ".join(c["reason"] for c in failed) + " — nothing will be added.")

        params["course_id"] = course.course_id
        params.setdefault("status", "not_taken")  # FC14 default
        description = f"Add {course.title} ({course.course_id}) to your profile"
        if params.get("semester_term"):
            description += f" for {params['semester_term']}"
        return description + f" with status {params['status']}", params

    def _propose_change_class_status(self, student_id: str, params: dict) -> Tuple[str, dict]:
        course_id, status = params.get("course_id", ""), params.get("status", "")
        if status not in CLASS_STATUSES:
            raise Refusal(f"{status!r} is not a valid class status — use one of: "
                          + ", ".join(CLASS_STATUSES) + " (FC21).")
        current = next((r for r in self.student_classes(student_id) if r.course_id == course_id), None)
        if current is None:
            raise Refusal(f"{course_id} is not on your profile yet — add it first (FC14), "
                          "then I can update its status (FC21).")
        return (f"Change {course_id} status from {current.status} to {status}",
                {"course_id": course_id, "status": status})

    def _propose_change_major(self, student_id: str, params: dict) -> Tuple[str, dict]:
        major_text, concentration = self._split_target(params.get("major_name", ""), params.get("concentration"))
        degree = self._resolve_major(major_text or "")
        if degree is None:
            raise Refusal(f"I couldn't match a major to {params.get('major_name')!r}. "
                          f"Offered: {self._major_names()}.")
        payload = {"major_name": degree.major_name}
        description = f"Change your major to {degree.major_name}"
        if concentration:
            match = next((n for n in degree.concentrations if n.lower() == concentration.lower()), None)
            if match is None and concentration.lower() != "general":
                raise Refusal(f"{degree.major_name} has no {concentration!r} concentration. "
                              f"Offered: {', '.join(degree.concentrations)}, General.")
            payload["concentration"] = match or "General"
            description += f" with the {payload['concentration']} concentration"
        return description + _REPLAN_NOTE, payload

    def _propose_change_concentration(self, student_id: str, params: dict) -> Tuple[str, dict]:
        concentration = (params.get("concentration") or "").strip()
        student = self.student_profile(student_id)
        if not concentration:
            raise Refusal("Which concentration would you like to switch to?")
        if student is None or not student.current_major:
            raise Refusal("You don't have a major on record yet — set a major first (FC1).")
        offered = self._offered_concentrations(student.current_major)
        if offered:
            match = next((n for n in offered if n.lower() == concentration.lower()), None)
            if match is None and concentration.lower() != "general":
                raise Refusal(f"{student.current_major} has no {concentration!r} concentration. "
                              f"Offered: {', '.join(offered)}, General.")
            concentration = match or "General"
        return (f"Change your concentration (currently {student.concentration or 'none set'}) "
                f"to {concentration}{_REPLAN_NOTE}", {"concentration": concentration})

    def _propose_change_degree(self, student_id: str, params: dict) -> Tuple[str, dict]:
        degree = self._aligned_degree(student_id, params.get("degree_id", ""))
        return (f"Set your tracked degree to {degree.degree_id} ({degree.major_name})",
                {"degree_id": degree.degree_id})

    def _propose_activate_plan(self, student_id: str, params: dict) -> Tuple[str, dict]:
        plans = self._sql.list_plans(student_id)
        wanted = params.get("plan_id")
        if wanted:
            plan = next((p for p in plans if p["plan_id"] == wanted), None)
            if plan is None:
                raise Refusal(f"No plan {wanted!r} on record.")
            if plan.get("is_active"):
                raise Refusal(f"Plan {plan['plan_id']} is already active.")
        else:
            plan = next((p for p in plans if not p.get("is_active")), None)
            if plan is None:
                raise Refusal("Your latest plan is already active — nothing to change." if plans
                              else "You have no plans yet — ask me to generate one first.")
        description = f"Make plan {plan['plan_id']} ({plan.get('target_major')}) your active plan"
        student = self.student_profile(student_id)
        track = plan.get("concentration") or "General"
        if student is not None and (student.current_major != plan.get("target_major")
                                    or (student.concentration or "General").lower() != track.lower()):
            # FC6/FC23: the profile follows the active plan — say so on the card.
            description += f"; your profile will switch to {plan.get('target_major')} — {track}"
        return description, {"plan_id": plan["plan_id"]}

    # ------------------------------------------------- step 2: confirm/cancel

    def check_decision(self, action_id: str, student_id: str, session_id: Optional[str]) -> Optional[dict]:
        """The open pending action, or None (reason in `decision_error()`)."""
        row = self._sql.get_pending_action(action_id)
        if row is None:
            error = f"No pending action {action_id!r} on record — the proposal may have been cancelled or purged."
        elif row["student_id"] != student_id:
            error = "That proposal belongs to a different student."
        elif session_id and row["session_id"] != session_id:
            error = "That proposal belongs to a different conversation."
        elif row["status"] != "open":
            error = f"That proposal was already resolved ({row['status']}) — nothing further was done."
        else:
            error = None
        self._decision_error = error
        return None if error else row

    def decision_error(self) -> Optional[str]:
        return self._decision_error

    def resolve_decision(self, action_row: dict, decision: str) -> dict:
        """Cancelled → close the row, change nothing. Confirmed → run the action."""
        if decision == "cancelled":
            self._sql.resolve_pending_action(action_row["action_id"], "cancelled")
            return {"done": False, "outcome": "Understood — cancelled, no changes were made.", "error": None}
        if decision != "confirmed":
            return {"done": False, "outcome": None, "error": f"Unknown decision {decision!r} — use confirm or cancel."}

        payload = action_row.get("payload") or {}
        if isinstance(payload, str):
            payload = json.loads(payload)
        action_type = action_row["action_type"]
        try:
            if action_type in _PLAN_EDITS:
                outcome = self._do_plan_edit(action_row["student_id"], action_type, payload)
            else:
                runner = {
                    "add_class": self._do_add_class,
                    "change_class_status": self._do_change_class_status,
                    "change_major": self._do_change_major,
                    "change_concentration": self._do_change_concentration,
                    "change_degree": self._do_change_degree,
                    "activate_plan": self._do_activate_plan,
                }.get(action_type)
                if runner is None:
                    raise Refusal(f"Unknown action type {action_type!r}.")
                outcome = runner(action_row["student_id"], payload)
        except Refusal as refusal:
            return {"done": False, "outcome": None, "error": str(refusal)}
        self._sql.resolve_pending_action(action_row["action_id"], "confirmed")
        return {"done": True, "outcome": outcome, "error": None}

    def _do_add_class(self, student_id: str, payload: dict) -> str:
        record = self._sql.add_student_class(
            student_id, payload["course_id"],
            status=payload.get("status", "not_taken"), semester_taken=payload.get("semester_term"))
        return f"Added {record.course_id} to your profile ({record.status})."

    def _do_change_class_status(self, student_id: str, payload: dict) -> str:
        record = self._sql.update_student_class(student_id, payload["course_id"], status=payload["status"])
        return f"Updated {record.course_id} — status is now {record.status}."

    def _do_change_major(self, student_id: str, payload: dict) -> str:
        student = self._sql.update_student_major(student_id, payload["major_name"], payload.get("concentration"))
        suffix = f" — {student.concentration}" if student.concentration else ""
        return (f"Your major is now {student.current_major}{suffix}. "
                + self._replan(student_id, {"target_major": student.current_major}))

    def _do_change_concentration(self, student_id: str, payload: dict) -> str:
        current = self.student_profile(student_id)
        student = self._sql.update_student_major(student_id, current.current_major, payload["concentration"])
        return f"Your concentration is now {student.concentration}. " + self._replan(student_id, {})

    def _replan(self, student_id: str, params: dict) -> str:
        """FC2/FC6: after a confirmed program change, DegreePlanGenerator builds
        a plan for the new major/track and it becomes the active plan, so the
        plan never lags the profile. The old plans stay on record (FC4/FC6)."""
        generated = self.generate_plan(student_id, params)
        if generated["refusal"]:
            return f"Your degree plan was NOT regenerated: {generated['refusal']}"
        plan = generated["plan"]
        return (f"A new degree plan {plan['plan_id']} ({plan['concentration']}) was generated "
                "and is now your active plan.")

    def _do_change_degree(self, student_id: str, payload: dict) -> str:
        degree = self._aligned_degree(student_id, payload["degree_id"])  # re-checked: state may have changed
        self._sql.set_selected_degree(student_id, degree.degree_id)
        return f"Your tracked degree is now {degree.degree_id}."

    def _do_activate_plan(self, student_id: str, payload: dict) -> str:
        if not self._sql.activate_plan(student_id, payload["plan_id"]):
            raise Refusal(f"Plan {payload['plan_id']!r} is no longer on record.")
        changed = self._sql.sync_profile_to_plan(student_id, payload["plan_id"])  # FC6
        suffix = (f" Your profile now tracks {changed['major_name']} — {changed['concentration']}."
                  if changed else "")
        return f"Plan {payload['plan_id']} is now your active plan.{suffix}"

    def _do_plan_edit(self, student_id: str, op: str, payload: dict) -> str:
        """Re-apply the edit to the current active plan and save a new version (FC3/FC4)."""
        plan, semesters, description, _ = self._edit_active_plan(student_id, op, payload)
        self._sql.create_plan_version(plan["plan_id"], {
            "semesters": semesters_payload([tuple(s) for s in semesters], self._sql.get_catalog()),
            "includes_summer": bool(plan.get("includes_summer")),
            "notes": plan.get("notes") or [],
        }, note="edited via assistant (FC3/FC23)")
        return f"Done — {description[0].lower() + description[1:]}."

    # ------------------------------------------------------------- helpers

    def _offered_concentrations(self, major_name: Optional[str]) -> list:
        """Concentration tracks of the degree that grants `major_name` (empty if none/unknown)."""
        degree = next((d for d in self._sql.list_degrees() if d.major_name == major_name), None)
        return degree.concentrations if degree else []

    def _aligned_degree(self, student_id: str, degree_id: str):
        """The degree, if it exists and matches the student's major (FC16)."""
        degree = self._degree_or_none(degree_id)
        if degree is None:
            raise Refusal(f"No degree on record with id {degree_id!r} — nothing will be changed.")
        student = self.student_profile(student_id)
        if student is not None and student.current_major and student.current_major != degree.major_name:
            raise Refusal(f"{degree.degree_id} is granted by {degree.major_name}, but "
                          f"your major is {student.current_major} (FC16 misalignment).")
        return degree

    def _edit_active_plan(self, student_id: str, op: str, params: dict):
        """Apply add/remove/move to a copy of the active plan's semesters.

        Returns (plan, new_semesters, description, normalized_payload). Refuses
        if the edit would ADD a blocking engine issue (e.g. FC30 repeat, FC32
        cap) that the plan didn't already have.
        """
        plan = self.active_plan(student_id)
        if plan is None:
            raise Refusal("You have no active plan (FC6) — ask me to generate one and make it active first.")
        # Each semester is [term, year, [course ids]].
        semesters: List[list] = [[s["term"], int(s["year"]), list(s.get("courses") or [])]
                                 for s in plan["semesters"]]
        before = [tuple(s[:2]) + (list(s[2]),) for s in semesters]

        raw = (params.get("course_id") or "").strip()
        course = self.find_course(raw)
        planned_ids = {cid for s in semesters for cid in s[2]}
        course_id = raw if raw in planned_ids else (course.course_id if course else raw)
        if op != "plan_remove_course" and course is None and course_id not in planned_ids:
            raise Refusal(f"There is no course on record for {raw!r} — nothing will be changed.")

        target = None
        if op in ("plan_add_course", "plan_move_course"):
            match = _TERM_RE.search(params.get("semester_term") or "")
            if not match:
                raise Refusal("Which semester of your plan (e.g. Fall 2027)?")
            target = (match.group(1).capitalize(), int(match.group(2)))
            if not any((s[0], s[1]) == target for s in semesters):
                offered = ", ".join(f"{s[0]} {s[1]}" for s in semesters)
                raise Refusal(f"{target[0]} {target[1]} isn't a semester in your active plan — "
                              f"its semesters are: {offered}.")
        target_sem = next((s for s in semesters if (s[0], s[1]) == target), None)
        current_sem = next((s for s in semesters if course_id in s[2]), None)
        label = course_id + (f" ({course.title})" if course else "")

        if op == "plan_remove_course":
            if current_sem is None:
                raise Refusal(f"{course_id} isn't in your active plan.")
            current_sem[2].remove(course_id)
            description = f"Remove {label} from your plan ({current_sem[0]} {current_sem[1]})"
        elif op == "plan_add_course":
            if current_sem is not None:
                raise Refusal(f"{course_id} is already in your plan ({current_sem[0]} {current_sem[1]}).")
            target_sem[2].append(course_id)
            description = f"Add {label} to your plan for {target[0]} {target[1]}"
        else:  # plan_move_course
            if current_sem is None:
                raise Refusal(f"{course_id} isn't in your active plan.")
            if current_sem is target_sem:
                raise Refusal(f"{course_id} is already in {target[0]} {target[1]}.")
            current_sem[2].remove(course_id)
            target_sem[2].append(course_id)
            description = f"Move {label} from {current_sem[0]} {current_sem[1]} to {target[0]} {target[1]}"

        # Only issues the edit introduces block it; pre-existing ones don't.
        records = self.student_classes(student_id)
        catalog = self._sql.get_catalog()
        degree = self._degree_or_none(plan["degree_id"])
        cap = degree.max_semester_credits if degree else None
        old_issues = {i["text"] for i in DegreePlanGenerator.review_plan_semesters(
            before, records, catalog, max_credits_per_sem=cap).blocking()}
        new_issues = [i["text"] for i in DegreePlanGenerator.review_plan_semesters(
            [tuple(s) for s in semesters], records, catalog, max_credits_per_sem=cap).blocking()
            if i["text"] not in old_issues]
        if new_issues:
            raise Refusal(" / ".join(new_issues) + " — nothing will be changed.")

        payload = {"plan_id": plan["plan_id"], "course_id": course_id,
                   "semester_term": f"{target[0]} {target[1]}" if target else None}
        return plan, semesters, description, payload
