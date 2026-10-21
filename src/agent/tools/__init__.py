"""LangChain/LangGraph tool bridges — thin wrappers over `core` + `database`.

Tools never contain constraint logic: schedule tools → SQLite (FC33 exact),
search tools → Chroma (FC33 semantic, FC9), plan tools → the deterministic
engine for audits/recommendations (FC24, FC29–FC32) + the FC23 proposal and
decision gate."""
from typing import List, Optional

from core.entities.course import Course, CourseSection
from core.entities.degree import DegreeRequirement
from core.entities.student import EnrollmentRecord, Student

from agent.tools.plan_tools import PlanTools
from agent.tools.schedule_tools import ScheduleTools
from agent.tools.search_tools import SearchTools


class AdvisorToolkit:
    """The single toolkit object graph nodes use (built per app process)."""

    def __init__(self, sql_db_manager, vector_db_manager=None) -> None:
        self._schedule = ScheduleTools(sql_db_manager)
        self._search = SearchTools(vector_db_manager)
        self._plan = PlanTools(sql_db_manager, vector_db_manager)
        self._sql = sql_db_manager

    # ---------------------------------------------------------- exact (SQL)

    def find_course(self, raw_id: str) -> Optional[Course]:
        return self._schedule.find_course(raw_id)

    def search_courses(self, query=None, department=None, term=None) -> List[Course]:
        return self._schedule.search_courses(query=query, department=department, term=term)

    def sections(self, course_id: str) -> List[CourseSection]:
        return self._schedule.sections(course_id)

    def student_profile(self, student_id: str) -> Optional[Student]:
        return self._schedule.student_profile(student_id)

    def student_classes(self, student_id: str) -> List[EnrollmentRecord]:
        return self._schedule.student_classes(student_id)

    def selected_degree(self, student_id: str) -> Optional[DegreeRequirement]:
        return self._schedule.selected_degree(student_id)

    def hours_by_ids(self, course_ids) -> dict:
        return self._schedule.hours_by_ids(course_ids)

    def degree_progress(self, student_id: str) -> Optional[dict]:
        return self._schedule.degree_progress(student_id)

    def active_plan(self, student_id: str) -> Optional[dict]:
        return self._schedule.active_plan(student_id)

    # ------------------------------------------------------ semantic (Chroma)

    def semantic_courses(self, query: str, k: int = 6) -> List[dict]:
        return self._search.semantic_courses(query, k=k)

    def catalog_search(self, query: str, k: int = 4) -> List[dict]:
        return self._search.catalog_search(query, k=k)

    # ------------------------------------- deterministic audits (FC24/29–32)

    def course_audit(self, student_id: str, course_raw: str, section_id=None):
        return self._plan.course_audit(student_id, course_raw, section_id)

    def recommend_candidates(self, student_id: str, query: Optional[str], k: int = 6) -> dict:
        return self._plan.recommend_candidates(student_id, query, k=k)

    def degree_audit(self, student_id: str, degree_id: Optional[str] = None):
        return self._plan.degree_audit(student_id, degree_id)

    # ------------------------------------------------- FC23 propose / decide

    def propose_action(self, student_id: str, session_id: str, action_type: str,
                       params: Optional[dict] = None) -> dict:
        return self._plan.propose_action(student_id, session_id, action_type, params)

    def check_decision(self, action_id: str, student_id: str, session_id=None):
        return self._plan.check_decision(action_id, student_id, session_id)

    def decision_error(self) -> Optional[str]:
        return self._plan._decision_error

    def resolve_decision(self, action_row: dict, decision: str) -> dict:
        return self._plan.resolve_decision(action_row, decision)

    # ------------------------------------------------------------ sessioning

    def ensure_chat_session(self, student_id: str) -> str:
        """FC27/FC34: continue the active session or open one lazily."""
        return self._sql.ensure_chat_session(student_id)

    def recent_history(self, student_id: str, session_id: str) -> List[str]:
        """FC27/FC34: trimmed turns from SQLite — raises RecordNotFoundError
        for an unknown session id (honest 404 at the HTTP layer)."""
        rows = self._sql.get_chat_history(student_id, session_id)
        return [f"{row['role']}: {str(row['content'])[:220]}" for row in rows[-12:]]