"""§2 DegreePlanGenerator (FC2, FC25, FC26) — the deterministic planning engine.

Pure code, entity-passed (monorepo dependency rule: no db/LLM imports here).
The LLM layer may call this through tools but can never bypass it, and plan
*writes* always flow through this module or the persisted validators.

Implemented adjustments vs. the domain-model outline (documented in the
domain-model notes):
- `generate_multi_year_plan` takes the student, the target degree, and a
  catalog dict (course_id → Course) instead of a db-backed `course_catalog`
  attribute — core stays offline.
- Returns a `PlanGenerationResult` (plan + grounded `notes`) so honest
  caveats ride with the plan instead of being invented away.
- `review_plan_semesters` gives the HTTP/API layer the FC29–FC32 verdicts
  for unsaved drafts (the deterministic stand-in the mock UI used to fake).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from core.entities.course import Course
from core.entities.degree import DegreeBlock, DegreePlan, DegreeRequirement, SemesterPlan
from core.entities.student import EnrollmentRecord, Student

_COMPLETED_STATUSES = frozenset({"passed", "taken"})
_STANDARD_FALLBACK_CAP = 18  # documented POC convention when no cap is on record
_SEASON_ORDER = {"Spring": 0, "Summer": 1, "Fall": 2}
_DEFAULT_START_TERM: Tuple[str, int] = ("Fall", 2026)  # matches the seed data era


@dataclass
class PlanGenerationResult:
    """Engine output: the persisted-ready DegreePlan + grounded caveats."""

    plan: DegreePlan
    notes: List[str] = field(default_factory=list)


@dataclass
class PlanReviewResult:
    """FC29–FC32 verdicts over a draft (the engine side of POST /plans/review)."""

    status: str  # "ok" | "issues"
    issues: List[str] = field(default_factory=list)
    semester_issues: Dict[str, List[dict]] = field(default_factory=dict)

    def blocking(self) -> List[dict]:
        """Issues that must reject a save (hard safeguard violations)."""
        return [
            issue
            for items in self.semester_issues.values()
            for issue in items
            if issue["severity"] == "blocking"
        ]


@dataclass
class PlanComparisonResult:
    """§2 compare_plans output (FC26): the plan diff plus grounded trade-offs."""

    retained: List[str] = field(default_factory=list)
    lost: List[str] = field(default_factory=list)
    added: List[str] = field(default_factory=list)
    retained_hours: int = 0
    lost_hours: int = 0
    added_hours: int = 0
    graduation_estimate: Optional[str] = None
    advantages: List[str] = field(default_factory=list)
    disadvantages: List[str] = field(default_factory=list)


class DegreePlanGenerator:
    """Deterministic roadmap generation — never the LLM, never invented data."""

    # ------------------------------------------------------------- FC2/FC25

    @staticmethod
    def generate_multi_year_plan(
        student: Student,
        target_degree: DegreeRequirement,
        courses_by_id: Dict[str, Course],
        include_summer: bool = False,
        max_credits_per_sem: Optional[int] = None,
        current_term: Optional[Tuple[str, int]] = None,
    ) -> PlanGenerationResult:
        """Semester-by-semester roadmap from the current term (FC2, FC25).

        Honors: FC30 (completed courses excluded), FC29 (prereqs placed in
        earlier semesters when prerequisite data exists), FC32 (per-semester
        cap from the degree / preferences / request, degree-total awareness).
        Unresolvable requirement rows and dry elective pools are reported in
        `notes` — never filled with invented courses.
        """
        notes: List[str] = []
        records = student.completed_courses if student else []
        completed = {
            r.course_id for r in records if r.status in _COMPLETED_STATUSES
        }
        in_progress = [r.course_id for r in records if r.status == "in_progress"]

        cap = max_credits_per_sem or target_degree.max_semester_credits or _STANDARD_FALLBACK_CAP
        if not (max_credits_per_sem or target_degree.max_semester_credits):
            notes.append(
                f"No per-semester cap on record for {target_degree.degree_id} — "
                f"applying the standard {_STANDARD_FALLBACK_CAP}-hour planning cap.")

        def hours_for(cid: str) -> Optional[int]:
            course = courses_by_id.get(cid)
            return course.credit_hours if course else None

        # 1. concrete requirement rows (block order), select-one groups resolved.
        required: List[str] = []
        for block in target_degree.blocks:
            if block.kind == "electives" or not block.courses:
                continue
            groups: Dict[str, List] = {}
            for row in block.courses:
                if row.course_id is None:
                    notes.append(
                        f"{block.name}: requirement row {row.course_code!r} has no "
                        "course-catalog match — excluded from the plan")
                    continue
                if row.option_group:
                    groups.setdefault(row.option_group, []).append(row)
                    continue
                required.extend(DegreePlanGenerator._require_single(
                    row.course_id, completed, in_progress, required, block.name, notes))
            for rows in groups.values():
                satisfied = next((r for r in rows if r.course_id in completed), None)
                if satisfied is not None:
                    notes.append(
                        f"{block.name}: select-one requirement already satisfied by "
                        f"{satisfied.course_id} (completed).")
                    continue
                pick = next((r for r in rows if r.course_id in courses_by_id), None)
                if pick is None:
                    notes.append(
                        f"{block.name}: select-one group has no catalog-backed option "
                        "— excluded")
                    continue
                required.extend(DegreePlanGenerator._require_single(
                    pick.course_id, completed, in_progress, required, block.name, notes))

        # 2. elective buckets filled from the grounded catalog pool.
        electives = DegreePlanGenerator._elective_picks(
            target_degree, courses_by_id, completed, set(required), hours_for, notes)
        placement_order = DegreePlanGenerator._order_courses(
            required + electives, courses_by_id)

        # 3. semester-by-semester placement from the current term onwards.
        # FC29 (planning semantics): a course enters a semester only when every
        # prerequisite is satisfied by records or an EARLIER semester — pending
        # or same-semester prerequisites defer it.
        start = current_term or _parse_term(
            DegreePlanGenerator._latest_in_progress_term(records)) or _DEFAULT_START_TERM
        plan = DegreePlan(
            plan_id="",  # assigned by the persistence layer
            student_id=student.student_id if student else "",
            degree_id=target_degree.degree_id,
            target_major=target_degree.major_name,
            concentration=getattr(student, "concentration", None),
            includes_summer=bool(include_summer),
        )
        semesters: List[SemesterPlan] = []
        placed_before: set = set(in_progress)
        if in_progress:
            semesters.append(SemesterPlan(term=start[0], year=start[1],
                                          course_ids=list(in_progress), max_credit_limit=cap))
        # placement starts after the in-progress semester when there is one
        terms = DegreePlanGenerator._term_sequence(start, include_summer)[1 if in_progress else 0:]
        remaining = list(placement_order)
        unknown_hours: List[str] = []
        term_index = 0
        while remaining and term_index < len(terms):
            term, year = terms[term_index]
            semester = SemesterPlan(term=term, year=year, course_ids=[], max_credit_limit=cap)
            semester_hours = 0
            progress = True
            while progress and remaining:
                progress = False
                for cid in list(remaining):
                    course = courses_by_id.get(cid)
                    hours = course.credit_hours if course else None
                    prereqs = course.prerequisites if course else []
                    if any(p in remaining for p in prereqs):
                        continue  # prerequisite still pending — wait for a later term
                    if any(p in semester.course_ids for p in prereqs):
                        continue  # prerequisite lands in this same semester — defer (FC29)
                    if hours is None and cid not in unknown_hours:
                        unknown_hours.append(cid)  # FC32 unverifiable — reported later
                    elif cap is not None and semester_hours + hours > cap:
                        continue  # doesn't fit this term; other courses still might
                    semester.course_ids.append(cid)
                    remaining.remove(cid)
                    semester_hours += hours or 0
                    progress = True
            if semester.course_ids:
                semesters.append(semester)
                placed_before.update(semester.course_ids)
            term_index += 1
        if unknown_hours:
            shown = ", ".join(sorted(unknown_hours)[:6]) + ("…" if len(unknown_hours) > 6 else "")
            notes.append(
                f"Credit hours are not on record for {len(unknown_hours)} planned "
                f"course(s) ({shown}) — FC32 could not verify their semesters.")
        if remaining:  # defensive: sequence is sized not to trigger
            notes.append(
                f"{len(remaining)} requirement course(s) could not be placed within "
                "the generated roadmap window.")
        plan.semesters = semesters
        return PlanGenerationResult(plan=plan, notes=notes)

    # --------------------------------------------------------------- FC26

    @staticmethod
    def compare_plans(
        existing_semesters: Sequence[SemesterPlan],
        new_semesters: Sequence[SemesterPlan],
        courses_by_id: Dict[str, Course],
    ) -> PlanComparisonResult:
        """Plan diff for a prospective major/concentration change (FC26).

        Deterministic set arithmetic over the two roadmaps plus grounded
        trade-off lines; hours come from the catalog, never guesswork.
        """
        flat_existing = [cid for s in DegreePlanGenerator._as_semesters(existing_semesters) for cid in s.course_ids]
        flat_new = [cid for s in DegreePlanGenerator._as_semesters(new_semesters) for cid in s.course_ids]
        existing_set, new_set = set(flat_existing), set(flat_new)
        existing_semesters = DegreePlanGenerator._as_semesters(existing_semesters)
        new_semesters = DegreePlanGenerator._as_semesters(new_semesters)

        def hours(ids: Iterable[str]) -> int:
            return sum((courses_by_id.get(cid).credit_hours or 0) for cid in ids
                       if courses_by_id.get(cid))

        retained = sorted(existing_set & new_set, key=lambda cid: DegreePlanGenerator._level(cid))
        lost = sorted(existing_set - new_set, key=lambda cid: DegreePlanGenerator._level(cid))
        added = sorted(new_set - existing_set, key=lambda cid: DegreePlanGenerator._level(cid))

        comparison = PlanComparisonResult(
            retained=retained, lost=lost, added=added,
            retained_hours=hours(retained), lost_hours=hours(lost), added_hours=hours(added),
        )
        last_new = new_semesters[-1] if new_semesters else None
        comparison.graduation_estimate = (
            f"{last_new.term} {last_new.year}" if last_new else None)

        if retained:
            comparison.advantages.append(
                f"{len(retained)} planned course(s) carry over "
                f"({comparison.retained_hours} hours).")
        else:
            comparison.disadvantages.append("None of the planned courses carry over.")
        if lost:
            comparison.disadvantages.append(
                f"{len(lost)} planned course(s) would no longer count "
                f"({comparison.lost_hours} hours): {', '.join(lost)}")
        else:
            comparison.advantages.append("None of your planned work is lost.")
        if added:
            comparison.disadvantages.append(
                f"{len(added)} course(s) newly required "
                f"({comparison.added_hours} hours): {', '.join(added)}")
        last_existing = existing_semesters[-1] if existing_semesters else None
        if last_new and last_existing:
            key_new = (last_new.year, _SEASON_ORDER.get(last_new.term, 0))
            key_old = (last_existing.year, _SEASON_ORDER.get(last_existing.term, 0))
            if key_new > key_old:
                comparison.disadvantages.append(
                    f"Graduation moves from {last_existing.term} {last_existing.year} "
                    f"to {last_new.term} {last_new.year}.")
            elif key_new < key_old:
                comparison.advantages.append(
                    f"Graduation moves earlier, to {last_new.term} {last_new.year}.")
            else:
                comparison.advantages.append("Graduation timeline is unchanged.")
        return comparison

    @staticmethod
    def simulate_major_switch(
        student: Student,
        new_degree: DegreeRequirement,
        courses_by_id: Dict[str, Course],
        include_summer: bool = False,
        max_credits_per_sem: Optional[int] = None,
        current_term: Optional[Tuple[str, int]] = None,
    ) -> PlanGenerationResult:
        """§2 Req 5a–c fuel: generate the would-be plan for a new degree (FC26)."""
        return DegreePlanGenerator.generate_multi_year_plan(
            student, new_degree, courses_by_id,
            include_summer=include_summer, max_credits_per_sem=max_credits_per_sem,
            current_term=current_term)

    # ---------------------------------------------------- draft review API

    @staticmethod
    def review_plan_semesters(
        semesters: Sequence[tuple],
        records,  # Sequence[EnrollmentRecord] or a Student (POC-tolerant)
        courses_by_id: Dict[str, Course],
        max_credits_per_sem: Optional[int] = None,
        current_term: Optional[Tuple[str, int]] = None,
    ) -> PlanReviewResult:
        """FC29–FC32 verdicts over an unsaved draft (POST /plans/review and
        the engine-side validation behind FC3 plan edits).

        `semesters` are (term, year, course_ids) tuples. Issue severities:
        blocking violations (FC30 re-planning a passed course, FC32 cap
        breach) must reject a save; FC29 ordering issues are warnings because
        prerequisite data is advisory for forward plans.
        """
        records = (records.completed_courses if isinstance(records, Student)
                   else records)
        completed = {r.course_id for r in records if r.status in _COMPLETED_STATUSES}
        underway = {r.course_id for r in records if r.status == "in_progress"}

        semester_issues: Dict[str, List[dict]] = {}
        issues: List[str] = []
        satisfied = set(completed) | set(underway)

        def issue(term: str, year: int, code: str, course: Optional[str],
                  text: str, severity: str) -> None:
            key = _semester_key(term, year)
            semester_issues.setdefault(key, []).append(
                {"code": code, "course": course, "text": text, "severity": severity})
            issues.append(text)

        for term, year, course_ids in semesters:
            semester_hours = 0
            for cid in course_ids:
                course = courses_by_id.get(cid)
                hours = course.credit_hours if course else None
                if cid in completed:
                    issue(term, year, "FC30", cid,
                          f"{cid} is already completed — remove it from the plan (FC30)",
                          "blocking")
                elif course is None:
                    issue(term, year, "FC33", cid,
                          f"{cid} is not in the course catalog (planned as-is)",
                          "warning")
                if hours:
                    semester_hours += hours
                for prereq in (course.prerequisites if course else []):
                    if prereq not in satisfied:
                        prefix = f"{prereq} (in progress)" if prereq in underway else prereq
                        issue(term, year, "FC29", cid,
                              f"{cid} needs {prefix} in an earlier semester", "warning")
                satisfied.add(cid)
            cap = max_credits_per_sem
            if cap and semester_hours > cap:
                issue(term, year, "FC32", None,
                      f"{term} {year} exceeds the {cap}-hour semester cap "
                      f"({semester_hours} planned)", "blocking")

        status = "issues" if issues else "ok"
        return PlanReviewResult(status=status, issues=issues, semester_issues=semester_issues)

    # ------------------------------------------------------------ internals

    @staticmethod
    def _require_single(cid, completed, in_progress, required, block_name, notes) -> List[str]:
        if cid in completed:
            notes.append(f"{block_name}: {cid} already completed — not re-planned (FC30).")
            return []
        if cid in in_progress:
            notes.append(f"{block_name}: {cid} is in progress this term — not re-planned.")
            return []
        if cid in required:
            return []
        return [cid]

    @staticmethod
    def _elective_picks(
        degree: DegreeRequirement,
        courses_by_id: Dict[str, Course],
        completed: set,
        reserved: set,
        hours_for,
        notes: List[str],
    ) -> List[str]:
        picks: List[str] = []
        for bucket_name, hours_required in degree.elective_rules.items():
            pool = DegreePlanGenerator._elective_pool(
                bucket_name, courses_by_id, completed, reserved | set(picks))
            filled = 0.0
            for cid in pool:
                if filled >= hours_required:
                    break
                hours = hours_for(cid)
                if not hours:
                    continue
                picks.append(cid)
                filled += hours
            if filled < hours_required:
                notes.append(
                    f"{bucket_name} unfulfilled by {hours_required - filled:g} hours — "
                    "the elective pool ran dry; nothing was invented.")
        return picks

    @staticmethod
    def _elective_pool(
        bucket_name: str,
        courses_by_id: Dict[str, Course],
        completed: set,
        reserved: set,
    ) -> List[str]:
        """Grounded candidates for a bucket like 'CSE 4000-level Technical
        Electives' or 'CSE 3000-level or 4000-level' — parsed from the
        requirement docs' wording; unparsable rules get an empty pool."""
        levels = [int(m) // 1000 for m in re.findall(r"(\d{4})-level", bucket_name)]
        if not levels:
            return []
        department_match = re.match(r"([A-Z]{2,4})\s", bucket_name)
        department = department_match.group(1) if department_match else None

        def qualifies(cid: str) -> bool:
            course = courses_by_id.get(cid)
            if course is None:
                return False
            department_of_id = course.department if course.department else (
                cid.split(" ")[0] if " " in cid else ("CSE" if cid.isdigit() else None))
            if department and department_of_id != department:
                return False
            try:
                return (int(DegreePlanGenerator._number(cid)) // 1000) in levels
            except (ValueError, TypeError):
                return False

        return sorted(
            (
                cid
                for cid in courses_by_id
                if cid not in completed and cid not in reserved and qualifies(cid)
            ),
            key=lambda cid: (int(DegreePlanGenerator._number(cid)), cid),
        )

    @staticmethod
    def _order_courses(
        course_ids: List[str], courses_by_id: Dict[str, Course]
    ) -> List[str]:
        """Kahn topological order over prerequisite edges (only when both
        endpoints are being placed), tie-broken by course level then id —
        deterministic and stable when prerequisite data is empty."""
        wanted = list(dict.fromkeys(course_ids))
        edges: Dict[str, List[str]] = {cid: [] for cid in wanted}
        indegree: Dict[str, int] = {cid: 0 for cid in wanted}
        for cid in wanted:
            course = courses_by_id.get(cid)
            for prereq in (course.prerequisites if course else []):
                if prereq in indegree and prereq != cid:
                    edges[prereq].append(cid)
                    indegree[cid] += 1
        ordered: List[str] = []
        ready = [cid for cid in wanted if indegree[cid] == 0]
        while ready:
            ready.sort(key=lambda cid: (DegreePlanGenerator._level(cid), cid))
            batch = ready[:]
            ready = []
            for cid in batch:
                ordered.append(cid)
                for dependent in edges[cid]:
                    indegree[dependent] -= 1
                    if indegree[dependent] == 0:
                        ready.append(dependent)
            ready = [cid for cid in ready if cid not in ordered]
        leftovers = [cid for cid in wanted if cid not in ordered]
        leftovers.sort(key=lambda cid: (DegreePlanGenerator._level(cid), cid))
        ordered = ordered + leftovers  # cycle remnants keep a deterministic spot
        # Re-sort by course level — prerequisite edges in this corpus run from
        # lower to higher numbered courses, so a stable re-sort keeps FC29
        # ordering while producing sane level-progressive roadmaps.
        ordered.sort(key=lambda cid: (DegreePlanGenerator._level(cid), cid))
        return ordered

    @staticmethod
    def _as_semesters(semesters) -> List[SemesterPlan]:
        """Accept SemesterPlan rows or (term, year, course_ids) tuples."""
        return [
            s if isinstance(s, SemesterPlan)
            else SemesterPlan(term=s[0], year=s[1], course_ids=list(s[2]))
            for s in semesters
        ]

    @staticmethod
    def _term_sequence(
        start: Tuple[str, int], include_summer: bool, capacity: int = 64
    ) -> List[Tuple[str, int]]:
        """From `start`: Fall → Spring → (Summer) → next Fall… deterministic."""
        sequence: List[Tuple[str, int]] = []
        term, year = start
        for _ in range(capacity):
            sequence.append((term, year))
            if term == "Fall":
                term, year = "Spring", year + 1  # academic-year crossover
            elif term == "Spring":
                if include_summer:
                    sequence.append(("Summer", year))
                term = "Fall"
            else:  # a Summer start continues into Fall
                term = "Fall"
        return sequence

    @staticmethod
    def _latest_in_progress_term(records: Sequence[EnrollmentRecord]) -> Optional[str]:
        for record in records:
            if record.status == "in_progress" and record.semester_taken:
                return record.semester_taken
        return None

    @staticmethod
    def _level(course_id: str) -> int:
        try:
            return int(DegreePlanGenerator._number(course_id))
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def _number(course_id: str) -> str:
        tail = course_id.split()[-1] if " " in course_id else course_id
        digits = re.sub(r"[^0-9]", "", tail)
        if not digits:
            raise ValueError(f"no numeric part in {course_id!r}")
        return digits


def semesters_payload(semesters, catalog: Dict[str, Course]) -> List[dict]:
    """Engine semesters → persisted/rendered payload with catalog-sourced
    credits (shared by the HTTP service and the agent toolkit)."""
    payload: List[dict] = []
    for semester in semesters:
        if isinstance(semester, tuple):
            term, year, course_ids = semester[0], semester[1], list(semester[2])
        else:  # core SemesterPlan
            term, year, course_ids = semester.term, semester.year, list(semester.course_ids)
        credits = sum(
            (catalog[cid].credit_hours or 0) for cid in course_ids if cid in catalog
        )
        payload.append({
            "term": term, "year": year, "courses": course_ids,
            "credits": credits or None,
        })
    return payload


def _semester_key(term: str, year: int) -> str:
    return f"{term.lower()}-{year}"


def _parse_term(text: Optional[str]) -> Optional[Tuple[str, int]]:
    if not text:
        return None
    match = re.match(r"(Fall|Spring|Summer)\s+(\d{4})", (text or "").strip(), re.IGNORECASE)
    if not match:
        return None
    return match.group(1).capitalize(), int(match.group(2))