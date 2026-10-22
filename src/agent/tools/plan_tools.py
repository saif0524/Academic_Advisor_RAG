"""Deterministic plan/audit/FC23 tooling — the validator's only doorway.

Any recommendation the agent gives flows through here: candidates are
validated by `CourseRecommendationValidator` (FC29–FC32) and only passing
candidates reach the summarizer. FC23 actions follow the confirm-before-
acting gate: deterministic prechecks at proposal time, persistence in the
`chat_pending_actions` table, execution ONLY on an explicit decision."""
from __future__ import annotations

import json
import re
import uuid
from typing import Dict, List, Optional, Sequence

from core.engine.generator import DegreePlanGenerator, semesters_payload
from core.entities.course import Course, CourseSection
from core.entities.degree import DegreeRequirement
from core.entities.student import Student
from core.engine.progress import compute_degree_progress
from core.engine.results import ConstraintCheck
from core.engine.validator import CourseRecommendationValidator

_FC21_STATUSES = ("not_taken", "in_progress", "passed", "failed", "taken")
_PLAN_EDIT_OPS = ("plan_add_course", "plan_remove_course", "plan_move_course")
_TERM_RE = re.compile(r"(Fall|Spring|Summer)\s+(\d{4})", re.IGNORECASE)


class PlanTools:
    """Toolset over the SQL manager (+ the vector manager for semantic pools).
    The validator in core owns every eligibility decision — this module only
    assembles inputs (student records, sections, hours, degree) from stores."""

    def __init__(self, sql_db_manager, vector_db_manager=None) -> None:
        from agent.tools.schedule_tools import ScheduleTools
        from agent.tools.search_tools import SearchTools

        self._sql = sql_db_manager
        self._schedule = ScheduleTools(sql_db_manager)
        self._search = SearchTools(vector_db_manager)
        self._decision_error: Optional[str] = None

    def find_course(self, raw_id: str) -> Optional[Course]:
        """Public passthrough for audit callers (§4 contract consumers)."""
        return self._schedule.find_course(raw_id)

    # ------------------------------------------------------------- FC24

    def course_audit(
        self, student_id: str, course_raw: str, section_id: Optional[str] = None
    ) -> Optional[dict]:
        """'Can I take X?' (FC24) — validate via the core engine (FC29–FC32).

        Returns None when the course isn't on record (the caller answers
        honestly; nothing is ever fabricated)."""
        course = self._schedule.find_course(course_raw)
        if course is None:
            return None
        records = self._sql.list_student_classes(student_id)
        degree = self._selected_degree(student_id)
        candidate = self._pick_section(course, section_id)
        result = CourseRecommendationValidator.verify_all_constraints(
            course=course,
            records=records,
            candidate_section=candidate,
            semester_sections=self._in_progress_sections(student_id, candidate),
            current_semester_hours=self._in_progress_hours(student_id, candidate),
            max_semester_credits=degree.max_semester_credits if degree else None,
            degree=degree,
            hours_by_id=self._hours_for([course.course_id] + [r.course_id for r in records]),
        )
        return {"course": self._course_payload(course), "result": result.payload()}

    def recommend_candidates(self, student_id: str, query: Optional[str], k: int = 6,
                             exclude_ids: Sequence[str] = ()) -> dict:
        """What should I take? (FC22, safeguarded) — semantic candidates when
        a query is given, the selected degree's remaining courses otherwise.
        EVERY candidate is validated (FC29–FC32); eligibility is code-owned."""
        pool = self._recommendation_pool(student_id, query, pool_size=k + len(exclude_ids))
        excluded = set(exclude_ids)
        # FC22: courses already on the active plan aren't re-suggested.
        already_planned = [c.course_id for c in pool if c.course_id in excluded]
        pool = [c for c in pool if c.course_id not in excluded][:k]
        records = self._sql.list_student_classes(student_id)
        degree = self._selected_degree(student_id)
        hours_by_id = self._hours_for(
            [c.course_id for c in pool] + [r.course_id for r in records])

        candidates: List[dict] = []
        for course in pool:
            result = CourseRecommendationValidator.verify_all_constraints(
                course=course,
                records=records,
                candidate_section=self._pick_section(course, None),
                semester_sections=self._in_progress_sections(student_id, None),
                current_semester_hours=0,
                max_semester_credits=degree.max_semester_credits if degree else None,
                degree=degree,
                hours_by_id=hours_by_id,
            )
            payload = result.payload()
            blocking = next((c for c in payload["checks"] if c["passed"] is False), None)
            candidates.append({
                "course_id": course.course_id,
                "title": course.title,
                "credit_hours": course.credit_hours,
                "eligible": payload["eligible"],
                "checks": payload["checks"],
                "reason": blocking["reason"] if blocking else "Eligible on every record check",
            })
        return {"query": query, "candidates": candidates,
                "already_planned": already_planned}

    def degree_audit(self, student_id: str, degree_id: Optional[str] = None) -> Optional[dict]:
        """Degree-requirements status (FC24, FC19 counting via core)."""
        try:
            degree = (self._sql.get_degree(degree_id) if degree_id
                      else self._selected_degree(student_id))
        except Exception:
            return None
        if degree is None:
            return None
        classes = self._sql.list_student_classes(student_id)
        totals = compute_degree_progress(degree, classes, self._hours_for(
            [c.course_id for c in classes]))
        checks = [
            ConstraintCheck(
                check_id="FC19", description=f"{degree.degree_id} · {line}",
                passed=None, reason=line.split(":", 1)[-1].strip(),
            ).payload()
            for line in totals["outstanding_requirements"]
        ]
        return {
            "degree_id": degree.degree_id,
            "major_name": degree.major_name,
            "completion_percent": totals["completion_percent"],
            "outstanding_requirements": totals["outstanding_requirements"],
            "checks": checks,
        }

    # ------------------------------------------------------- FC2/FC25 plans

    def generate_plan(self, student_id: str, params: Optional[dict] = None) -> dict:
        """"Generate a degree plan" requests — DegreePlanGenerator owns the
        math (FC2/FC25); this only assembles inputs from stores, persists the
        result, and reports grounded notes. Never the LLM's job."""
        params = dict(params or {})
        student = self._sql.get_student_record(student_id)
        if student is None:
            student = Student(student_id=student_id)
        student.completed_courses = self._sql.list_student_classes(student_id)

        target_major = params.get("target_major")
        degree = (self._resolve_major(target_major) if target_major
                  else self._selected_degree(student_id))
        if degree is None:
            names = "; ".join(sorted(d.major_name for d in self._sql.list_degrees()))
            refusal = (
                f"I couldn't match a degree plan to {target_major!r} — offered "
                f"majors: {names}." if target_major
                else ("You don't have a major or selected degree on record yet — "
                      "set your major first (FC1) and I can generate from there."))
            return {"plan": None, "notes": [], "refusal": refusal}

        catalog = self._catalog_dict()
        prefs = self._sql.get_student_preferences(student_id) or {}
        include_summer = bool(params.get("include_summer")) or bool(prefs.get("include_summer"))
        cap = params.get("max_credits_per_semester") or prefs.get("max_credits_per_semester")
        result = DegreePlanGenerator.generate_multi_year_plan(
            student, degree, catalog,
            include_summer=include_summer, max_credits_per_sem=cap)
        result.plan.plan_id = f"plan-{uuid.uuid4().hex[:10]}"
        payload = {
            "semesters": semesters_payload(result.plan.semesters, catalog),
            "includes_summer": result.plan.includes_summer,
            "notes": list(result.notes),
        }
        self._sql.save_degree_plan(result.plan, payload=payload)
        return {
            "plan": {
                "plan_id": result.plan.plan_id,
                "target_major": result.plan.target_major,
                "concentration": result.plan.concentration,
                "includes_summer": result.plan.includes_summer,
                "semesters": payload["semesters"],
            },
            "notes": list(result.notes),
            "refusal": None,
        }

    def _catalog_dict(self):
        """course_id → Course snapshot incl. prerequisite rows (FC29 fuel)."""
        by_id = {c.course_id: c for c in self._sql.list_courses()}
        for row in self._sql.execute_query(
                "SELECT course_id, required_course_id FROM course_prerequisites "
                "WHERE kind = 'prereq'"):
            course = by_id.get(row["course_id"])
            if course is not None and row["required_course_id"] not in course.prerequisites:
                course.prerequisites.append(row["required_course_id"])
        return by_id

    # ----------------------------------------------------- FC23 proposals

    def propose_action(
        self, student_id: str, session_id: str, action_type: str, params: Optional[dict] = None,
    ) -> dict:
        """Deterministic prechecks → pending-action row (persisted, open), or
        an honest in-band refusal. Nothing is written on the profile here."""
        params = dict(params or {})
        refusal = None

        if action_type == "add_class":
            course = self._schedule.find_course(params.get("course_id", ""))
            if course is None:
                refusal = (f"There is no course on record for {params.get('course_id')!r}"
                           " — nothing will be added.")
            else:
                records = self._sql.list_student_classes(student_id)
                existing = next((r for r in records if r.course_id == course.course_id), None)
                if existing is not None and existing.status in {"passed", "taken"}:
                    refusal = (f"{course.course_id} is already completed on your record "
                               "(FC30) — it cannot be added again.")
                elif existing is not None and existing.status == "in_progress":
                    refusal = f"{course.course_id} is already in progress this semester."
                else:
                    degree = self._selected_degree(student_id)
                    payload_result = CourseRecommendationValidator.verify_all_constraints(
                        course=course, records=records,
                        candidate_section=None, semester_sections=(),
                        current_semester_hours=0,
                        max_semester_credits=degree.max_semester_credits if degree else None,
                        degree=degree,
                        hours_by_id=self._hours_for(
                            [course.course_id] + [r.course_id for r in records]),
                    ).payload()
                    failed = [c for c in payload_result["checks"]
                              if c["passed"] is False and c["check_id"] in {"FC29", "FC30", "FC32"}]
                    if failed:
                        refusal = " / ".join(c["reason"] for c in failed) + " — nothing will be added."
                    else:
                        params.setdefault("status", "not_taken")  # FC14 default
                        params["course_id"] = course.course_id
                        description = f"Add {course.title} ({course.course_id}) to your profile"
                        if params.get("semester_term"):
                            description += f" for {params['semester_term']}"
                        description += f" with status {params['status']}"
                        return self._create(student_id, session_id, "add_class", description, params)

        elif action_type == "change_class_status":
            course_id = params.get("course_id", "")
            status = params.get("status", "")
            if status not in _FC21_STATUSES:
                refusal = (f"{status!r} is not a valid class status — use one of: "
                           + ", ".join(_FC21_STATUSES) + " (FC21).")
            else:
                current = self._sql.execute_query(
                    "SELECT status FROM student_classes WHERE student_id = ? AND course_id = ?",
                    (student_id, course_id))
                if not current:
                    refusal = (f"{course_id} is not on your profile yet — add it first "
                               "(FC14), then I can update its status (FC21).")
                else:
                    description = (f"Change {course_id} status "
                                   f"from {current[0]['status']} to {status}")
                    return self._create(
                        student_id, session_id, "change_class_status", description,
                        {"course_id": course_id, "status": status})

        elif action_type == "change_major":
            major = self._resolve_major(params.get("major_name", ""))
            if major is None:
                names = "; ".join(sorted(d.major_name for d in self._sql.list_degrees()))
                refusal = (f"I couldn't match a major to {params.get('major_name')!r}. "
                           f"Offered: {names}.")
            else:
                description = f"Change your major to {major.major_name}"
                return self._create(student_id, session_id, "change_major", description,
                                    {"major_name": major.major_name})

        elif action_type == "change_concentration":
            concentration = (params.get("concentration") or "").strip()
            student = self._sql.get_student_record(student_id)
            if not concentration:
                refusal = "Which concentration would you like to switch to?"
            elif student is None or not student.current_major:
                refusal = "You don't have a major on record yet — set a major first (FC1)."
            else:
                description = (f"Change your concentration "
                               f"(currently {student.concentration or 'none set'}) "
                               f"to {concentration}")
                return self._create(student_id, session_id, "change_concentration",
                                    description, {"concentration": concentration})

        elif action_type == "change_degree":
            degree_id = params.get("degree_id", "")
            try:
                degree = self._sql.get_degree(degree_id)
            except Exception:
                degree = None
            if degree is None:
                refusal = f"No degree on record with id {degree_id!r} — nothing will be changed."
            else:
                student = self._sql.get_student_record(student_id)
                if (student is not None and student.current_major
                        and student.current_major != degree.major_name):
                    refusal = (f"{degree.degree_id} is granted by {degree.major_name}, but "
                               f"your major is {student.current_major} (FC16 misalignment).")
                else:
                    description = (f"Set your tracked degree to {degree.degree_id} "
                                   f"({degree.major_name})")
                    return self._create(student_id, session_id, "change_degree", description,
                                        {"degree_id": degree.degree_id})
        elif action_type in _PLAN_EDIT_OPS:
            proposal, refusal = self._precheck_plan_edit(student_id, action_type, params)
            if proposal is not None:
                return self._create(student_id, session_id, action_type,
                                    proposal["description"], proposal["payload"])

        elif action_type == "activate_plan":
            proposal, refusal = self._precheck_activation(student_id, params)
            if proposal is not None:
                return self._create(student_id, session_id, action_type,
                                    proposal["description"], proposal["payload"])
        else:
            refusal = f"Unsupported action {action_type!r} on your behalf (FC23)."

        return {"proposed": None, "refusal": refusal or "I couldn't prepare that action."}

    # ----------------------------------------------------- FC23 decisions

    def check_decision(
        self, action_id: str, student_id: str, session_id: Optional[str]
    ) -> Optional[dict]:
        """The FC23 gate (defensive recheck behind the service's validation).
        Returns the open action row, or None with `decision_error` set."""
        self._decision_error = None
        row = self._sql.get_pending_action(action_id)
        if row is None:
            self._decision_error = (f"No pending action {action_id!r} on record — "
                                    "the proposal may have been cancelled or purged.")
            return None
        if row["student_id"] != student_id:
            self._decision_error = "That proposal belongs to a different student."
            return None
        if session_id and row["session_id"] != session_id:
            self._decision_error = "That proposal belongs to a different conversation."
            return None
        if row["status"] != "open":
            self._decision_error = ("That proposal was already resolved ("
                                    + row["status"] + ") — nothing further was done.")
            return None
        return row

    def resolve_decision(self, action_row: dict, decision: str) -> dict:
        """Confirmed → deterministic execution (then 'confirmed');
        cancelled → resolved with no write (FC23)."""
        if decision == "cancelled":
            self._sql.resolve_pending_action(action_row["action_id"], "cancelled")
            return {"done": False,
                    "outcome": "Understood — cancelled, no changes were made.",
                    "error": None}
        if decision != "confirmed":
            return {"done": False, "outcome": None,
                    "error": f"Unknown decision {decision!r} — use confirm or cancel."}
        payload = self._payload_of(action_row)
        outcome, error = self._execute(action_row["student_id"], action_row["action_type"], payload)
        if error:
            return {"done": False, "outcome": None, "error": error}
        self._sql.resolve_pending_action(action_row["action_id"], "confirmed")
        return {"done": True, "outcome": outcome, "error": None}

    # ------------------------------------------------------------ plumbing

    def _execute(self, student_id: str, action_type: str, payload: dict):
        """Deterministic writes (FC14/FC21/FC1/FC7/FC16/FC17) per action kind."""
        if action_type == "add_class":
            record = self._sql.add_student_class(
                student_id, payload["course_id"],
                status=payload.get("status", "not_taken"),
                semester_taken=payload.get("semester_term"))
            return f"Added {record.course_id} to your profile ({record.status}).", None
        if action_type == "change_class_status":
            record = self._sql.update_student_class(
                student_id, payload["course_id"], status=payload["status"])
            return f"Updated {record.course_id} — status is now {record.status}.", None
        if action_type == "change_major":
            student = self._sql.update_student_major(
                student_id, payload["major_name"], payload.get("concentration"))
            return (f"Your major is now {student.current_major}"
                    f"{' — ' + student.concentration if student.concentration else ''}."), None
        if action_type == "change_concentration":
            student_now = self._sql.get_student_record(student_id)
            student = self._sql.update_student_major(
                student_id, student_now.current_major, payload["concentration"])
            return f"Your concentration is now {student.concentration}.", None
        if action_type == "change_degree":
            try:
                degree = self._sql.get_degree(payload["degree_id"])
            except Exception:
                degree = None
            student = self._sql.get_student_record(student_id)
            if degree is None:
                return None, f"Degree {payload['degree_id']!r} is no longer on record."
            if (student is not None and student.current_major
                    and student.current_major != degree.major_name):
                return None, (f"{degree.degree_id} is not aligned to your major "
                              "(FC16) — nothing was changed.")
            self._sql.set_selected_degree(student_id, degree.degree_id)
            return f"Your tracked degree is now {degree.degree_id}.", None
        if action_type in _PLAN_EDIT_OPS:
            return self._execute_plan_edit(student_id, action_type, payload)
        if action_type == "activate_plan":
            if not self._sql.activate_plan(student_id, payload["plan_id"]):
                return None, f"Plan {payload['plan_id']!r} is no longer on record."
            return f"Plan {payload['plan_id']} is now your active plan.", None
        return None, f"Unknown action type {action_type!r}."

    # ------------------------------------------------ FC3 plan edits (FC23)

    def _apply_plan_edit(self, student_id: str, op: str, params: dict):
        """Pure edit of the ACTIVE plan's semesters + deterministic review.
        Returns (plan, new_semesters, description, normalized_payload, refusal).
        Blocking engine verdicts (FC30 completed course, FC32 cap) that the
        edit INTRODUCES are refusals; pre-existing/advisory issues are not."""
        plan = self._sql.get_active_plan(student_id)
        if plan is None:
            return None, None, None, None, (
                "You have no active plan (FC6) — ask me to generate one and make "
                "it active first.")
        sems = [[s["term"], int(s["year"]), list(s.get("courses") or [])]
                for s in plan["semesters"]]
        raw = (params.get("course_id") or "").strip()
        course = self._schedule.find_course(raw)
        in_plan = {cid for s in sems for cid in s[2]}
        course_id = (raw if raw in in_plan
                     else (course.course_id if course else raw))
        if op != "plan_remove_course" and course is None and course_id not in in_plan:
            return None, None, None, None, (
                f"There is no course on record for {raw!r} — nothing will be changed.")

        target = None
        if op in ("plan_add_course", "plan_move_course"):
            match = _TERM_RE.search(params.get("semester_term") or "")
            if not match:
                return None, None, None, None, "Which semester of your plan (e.g. Fall 2027)?"
            target = (match.group(1).capitalize(), int(match.group(2)))
            if not any((s[0], s[1]) == target for s in sems):
                offered = ", ".join(f"{s[0]} {s[1]}" for s in sems)
                return None, None, None, None, (
                    f"{target[0]} {target[1]} isn't a semester in your active plan — "
                    f"its semesters are: {offered}.")

        located = next((s for s in sems if course_id in s[2]), None)
        label = f"{course_id}" + (f" ({course.title})" if course else "")
        if op == "plan_remove_course":
            if located is None:
                return None, None, None, None, f"{course_id} isn't in your active plan."
            located[2].remove(course_id)
            description = f"Remove {label} from your plan ({located[0]} {located[1]})"
        elif op == "plan_add_course":
            if located is not None:
                return None, None, None, None, (
                    f"{course_id} is already in your plan ({located[0]} {located[1]}).")
            next(s for s in sems if (s[0], s[1]) == target)[2].append(course_id)
            description = f"Add {label} to your plan for {target[0]} {target[1]}"
        else:  # plan_move_course
            if located is None:
                return None, None, None, None, f"{course_id} isn't in your active plan."
            if (located[0], located[1]) == target:
                return None, None, None, None, f"{course_id} is already in {target[0]} {target[1]}."
            located[2].remove(course_id)
            next(s for s in sems if (s[0], s[1]) == target)[2].append(course_id)
            description = (f"Move {label} from {located[0]} {located[1]} "
                           f"to {target[0]} {target[1]}")

        records = self._sql.list_student_classes(student_id)
        catalog = self._catalog_dict()
        try:
            cap = self._sql.get_degree(plan["degree_id"]).max_semester_credits
        except Exception:
            cap = None
        before = DegreePlanGenerator.review_plan_semesters(
            [(s["term"], int(s["year"]), list(s.get("courses") or [])) for s in plan["semesters"]],
            records, catalog, max_credits_per_sem=cap).blocking()
        after = DegreePlanGenerator.review_plan_semesters(
            [tuple(s) for s in sems], records, catalog, max_credits_per_sem=cap).blocking()
        known = {i["text"] for i in before}
        new_blocking = [i["text"] for i in after if i["text"] not in known]
        if new_blocking:
            return None, None, None, None, " / ".join(new_blocking) + " — nothing will be changed."
        normalized = {"plan_id": plan["plan_id"], "course_id": course_id,
                      "semester_term": f"{target[0]} {target[1]}" if target else None}
        return plan, sems, description, normalized, None

    def _precheck_plan_edit(self, student_id: str, op: str, params: dict):
        plan, _, description, payload, refusal = self._apply_plan_edit(student_id, op, params)
        if refusal:
            return None, refusal
        return {"description": description, "payload": payload}, None

    def _precheck_activation(self, student_id: str, params: dict):
        rows = self._sql.list_plans(student_id)
        wanted = params.get("plan_id")
        inactive = [r for r in rows if not r.get("is_active")]
        if wanted:
            row = next((r for r in rows if r["plan_id"] == wanted), None)
            if row is None:
                return None, f"No plan {wanted!r} on record."
        elif inactive:
            row = inactive[0]  # newest unactivated draft (list is newest-first)
        elif rows:
            return None, "Your latest plan is already active — nothing to change."
        else:
            return None, "You have no plans yet — ask me to generate one first."
        if row.get("is_active"):
            return None, f"Plan {row['plan_id']} is already active."
        return {"description": (f"Make plan {row['plan_id']} "
                                f"({row.get('target_major')}) your active plan"),
                "payload": {"plan_id": row["plan_id"]}}, None

    def _execute_plan_edit(self, student_id: str, op: str, payload: dict):
        """Confirmed turn: re-run the same deterministic edit on the CURRENT
        plan (state may have changed since the proposal) and save a new
        version (FC4)."""
        plan, sems, description, _, refusal = self._apply_plan_edit(student_id, op, payload)
        if refusal:
            return None, refusal
        catalog = self._catalog_dict()
        self._sql.create_plan_version(plan["plan_id"], {
            "semesters": semesters_payload([tuple(s) for s in sems], catalog),
            "includes_summer": bool(plan.get("includes_summer")),
            "notes": plan.get("notes") or [],
        }, note="edited via assistant (FC3/FC23)")
        return f"Done — {description[0].lower() + description[1:]}.", None

    def _create(self, student_id: str, session_id: str, action_type: str,
                description: str, params: dict) -> dict:
        action_id = self._sql.create_pending_action(
            session_id, student_id, action_type, description, params)
        return {"proposed": {
            "action_id": action_id,
            "session_id": session_id,
            "action_type": action_type,
            "description": description,
            "payload": json.dumps(params),  # stored form (tests parse the string)
            "status": "open",
        }, "refusal": None}

    def _recommendation_pool(
        self, student_id: str, query: Optional[str], pool_size: int
    ) -> List[Course]:
        """Semantic hits first (FC9); a selected degree's remaining requirement
        rows as the grounded fallback when the search misses (FC19 math)."""
        pool: List[Course] = []
        if query and query.strip():
            for hit in self._search.semantic_courses(query, k=pool_size + 4):
                pool.append(self._course_from_hit(hit))
        if not pool:
            pool = self._degree_pool(student_id)
        deduped: List[Course] = []
        seen: set = set()
        for course in pool:
            if course.course_id in seen:
                continue
            seen.add(course.course_id)
            deduped.append(course)
        return deduped[:pool_size]

    def _degree_pool(self, student_id: str) -> List[Course]:
        degree = self._selected_degree(student_id)
        if degree is None:
            return []
        completed = {r.course_id for r in self._sql.list_student_classes(student_id)
                     if r.status in {"passed", "taken", "in_progress"}}
        pool, seen = [], set()
        for block in degree.blocks:
            if block.kind == "electives" or not block.courses:
                continue
            for row in block.courses:
                if row.course_id and row.course_id not in completed and row.course_id not in seen:
                    seen.add(row.course_id)
                    try:
                        pool.append(self._sql.get_course(row.course_id))
                    except Exception:
                        continue  # missing catalog row — skipped honestly
        return pool

    def _pick_section(self, course: Course, section_id: Optional[str]) -> Optional[CourseSection]:
        sections = self._sql.list_sections(course.course_id)
        if section_id:
            return next((s for s in sections if s.section_id == section_id), None)
        if len(sections) == 1:
            return sections[0]  # deterministic single-section precheck
        return None

    def _in_progress_sections(
        self, student_id: str, candidate: Optional[CourseSection]
    ) -> List[CourseSection]:
        """Sections of the student's in-progress courses in the relevant term
        (the candidate's own section is excluded to avoid self-conflicts)."""
        in_progress = [r for r in self._sql.list_student_classes(student_id)
                       if r.status == "in_progress"]
        sections: List[CourseSection] = []
        for record in in_progress:
            for section in self._sql.list_sections(record.course_id):
                if candidate is None or section.semester_term == candidate.semester_term:
                    if candidate is None or section.section_id != candidate.section_id:
                        sections.append(section)
        return sections

    def _in_progress_hours(
        self, student_id: str, candidate: Optional[CourseSection]
    ) -> int:
        in_progress = [r for r in self._sql.list_student_classes(student_id)
                       if r.status == "in_progress"]
        if not in_progress:
            return 0
        hours = self._hours_for([r.course_id for r in in_progress])
        return sum((hours.get(r.course_id) or 0) for r in in_progress)

    def _selected_degree(self, student_id: str) -> Optional[DegreeRequirement]:
        student = self._sql.get_student_record(student_id)
        if student is None or not student.selected_degree_id:
            return None
        try:
            return self._sql.get_degree(student.selected_degree_id)
        except Exception:
            return None

    def _resolve_major(self, raw: str) -> Optional[DegreeRequirement]:
        text = (raw or "").strip().upper()
        if len(text) < 4:  # POC guard: pronouns/short fragments match nothing
            return None
        for degree in self._sql.list_degrees():
            if text in degree.major_name.upper():
                return degree
        return None

    def _hours_for(self, course_ids: Sequence[str]) -> Dict[str, int]:
        ids = list({c for c in course_ids if c})
        if not ids:
            return {}
        placeholders = ", ".join("?" for _ in ids)
        rows = self._sql.execute_query(
            f"SELECT course_id, credit_hours FROM courses WHERE course_id IN ({placeholders})",
            tuple(ids),
        )
        return {r["course_id"]: r["credit_hours"] for r in rows if r["credit_hours"] is not None}

    def _course_payload(self, course: Course) -> dict:
        return {
            "course_id": course.course_id,
            "title": course.title,
            "description": course.description,
            "credit_hours": course.credit_hours,
            "prerequisites": course.prerequisites,
            "corequisites": course.corequisites,
        }

    def _course_from_hit(self, hit: dict) -> Course:
        return Course(
            course_id=hit["course_id"], title=hit["title"],
            description=hit.get("description"), credit_hours=hit.get("credit_hours"),
        )

    @staticmethod
    def _payload_of(action_row: dict) -> dict:
        payload = action_row.get("payload") or {}
        return json.loads(payload) if isinstance(payload, str) else payload