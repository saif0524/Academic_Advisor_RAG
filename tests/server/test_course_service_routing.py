"""CourseService routing tests (FC33) — structured vs semantic split.

Service-level orchestration with faked managers (per the tester skill:
db managers are faked/overridden, never reached through the LLM). Proves the
data-type routing rule: exact lookups → SQLite; natural-language → Chroma.
"""


class RecordingFakeSQL:
    """Fake standing in for SQLDatabaseManager: records calls, returns data."""

    def __init__(self, courses):
        self.calls = []
        self._courses = courses

    def list_courses(self, query=None, department=None, term=None):
        self.calls.append(("list_courses", query, department, term))
        return self._courses

    def get_course(self, course_id):
        self.calls.append(("get_course", course_id))
        from database.errors import RecordNotFoundError

        raise RecordNotFoundError("Unknown course '9999'")

    def list_course_prerequisites(self, course_id):
        self.calls.append(("list_course_prerequisites", course_id))
        return [], []

    def list_sections(self, course_id):
        self.calls.append(("list_sections", course_id))
        return []


class RecordingFakeVector:
    def __init__(self, hits):
        self.calls = []
        self._hits = hits

    def similarity_search(self, collection, query, k=5, where=None):
        self.calls.append(("similarity_search", collection, query, k))
        return self._hits


def _course(course_id="3330", title="DATABASE SYSTEMS AND FILE STRUCTURES"):
    from core.entities.course import Course

    return Course(course_id=course_id, title=title, description="Relational model.", credit_hours=3)


def test_exact_search_routes_to_sql_only():
    """FC33: keyword search (FC8/FC10) consults SQLite; Chroma is not touched."""
    from server.services.courses import CourseService

    sql = RecordingFakeSQL([_course()])
    vec = RecordingFakeVector([{"id": "course:3330", "text": "x", "metadata": {}}])
    response = CourseService(sql_db_manager=sql, vector_db_manager=vec).search_exact(
        query="database", department=None, term=None
    )
    assert [call[0] for call in sql.calls] == ["list_courses"]
    assert vec.calls == []  # the split: vector store never consulted
    assert response.source == "sql"
    assert response.count == 1
    assert response.results[0].course_id == "3330"


def test_semantic_search_routes_to_chroma_only():
    """FC33: natural-language search (FC9) consults Chroma; SQLite never queried."""
    from server.services.courses import CourseService

    sql = RecordingFakeSQL([])
    vec = RecordingFakeVector([
        {"id": "course:3330", "text": "DATABASE SYSTEMS. Relational model.",
         "metadata": {"course_id": "3330", "title": "DATABASE SYSTEMS AND FILE STRUCTURES", "credit_hours": 3}},
    ])
    response = CourseService(sql_db_manager=sql, vector_db_manager=vec).search_semantic(
        "how do databases store relations?"
    )
    assert [call[0] for call in vec.calls] == ["similarity_search"]
    assert sql.calls == []
    assert response.source == "chroma"
    assert response.results[0].course_id == "3330"


def test_semantic_search_empty_hits_stay_empty():
    """FC9/FC33: zero similarity hits → empty result honestly (no backfill
    from the other store)."""
    from server.services.courses import CourseService

    sql = RecordingFakeSQL([_course()])  # SQL has data — must NOT be used as filler
    vec = RecordingFakeVector([])
    response = CourseService(sql_db_manager=sql, vector_db_manager=vec).search_semantic("klingon poetry courses")
    assert response.results == []
    assert response.count == 0
    assert response.source == "chroma"