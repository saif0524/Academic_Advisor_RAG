"""Ingest loader tests (FC33, FC35 seed corpus) — grounded in data/ files only.

These tests pin the *real* numbers found in the seed files so any fabricated
or lossy parse fails loudly. No mock data is introduced here: every expected
value is cross-derived from the checked-in data files.
"""
from pathlib import Path

import pytest

from database.ingest.catalog_text_loader import load_catalog_documents
from database.ingest.course_desc_loader import load_course_desc
from database.ingest.degree_requirements_loader import (
    derive_courses_from_requirements,
    load_degree_requirements,
)
from core.entities.course import Course

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


# ------------------------------------------------------- course corpus (FC35)

def test_course_desc_loader_reads_all_75_seed_courses():
    """FC33/FC35: the 75-course course-desc.json corpus loads losslessly."""
    courses = load_course_desc(DATA_DIR)
    assert len(courses) == 75
    assert all(isinstance(c, Course) for c in courses)
    assert all(c.department == "CSE" for c in courses)

    first = courses[0]
    assert first.course_id == "1000"
    assert first.title == "FRESHMAN UNDERGRADUATE RESEARCH"
    assert first.description == "Freshman level undergraduate research course."

    # No fabricated fields: descriptions present, credits unknown at corpus stage
    assert all(c.credit_hours is None for c in courses)


def test_course_to_document_chunk_has_title_and_description():
    """FC35: chunk format for embeddings carries title + description."""
    course = Course(course_id="3330", title="DATABASE SYSTEMS", description="File structures.")
    chunk = course.to_document_chunk()
    assert "DATABASE SYSTEMS" in chunk
    assert "File structures" in chunk


# ------------------------------------------- degree requirements (FC15/FC18)

@pytest.mark.parametrize("degree_id,total,max_credits", [("BS-CS", 121, 18), ("BS-SE", 120, 18)])
def test_degree_loader_parses_header_totals(degree_id, total, max_credits):
    """FC18: JSON header totals parse exactly (no rounding, no invention)."""
    degrees = {d.degree_id: d for d in load_degree_requirements(DATA_DIR)}
    deg = degrees[degree_id]
    assert deg.total_credits_required == total
    assert deg.max_semester_credits == max_credits
    assert deg.degree_id == degree_id
    assert deg.major_name.startswith("Bachelor of Science in")


def test_degree_loader_bs_cs_core_contains_requirement_rows():
    """FC18: every major-core row lands in core_courses using normalized ids
    (4-digit corpus id when the corpus has the course)."""
    degrees = {d.degree_id: d for d in load_degree_requirements(DATA_DIR)}
    bs_cs = degrees["BS-CS"]
    for expected in ("1105", "1310", "1320", "2315", "3320", "3318", "4392"):
        assert expected in bs_cs.core_courses, f"missing core course {expected}"
    # SE-only courses must NOT leak into the CS core
    assert "2381" not in bs_cs.core_courses


def test_requirement_courses_missing_from_corpus_keep_full_code_ids():
    """Grounded normalization: CSE 2320/CSE 2381 are NOT in course-desc.json,
    so they keep their full code as identity — no silent invention of a
    4-digit id the catalog never had."""
    degrees = {d.degree_id: d for d in load_degree_requirements(DATA_DIR)}
    assert "CSE 2320" in degrees["BS-CS"].core_courses
    assert "CSE 2381" in degrees["BS-SE"].core_courses
    # and corpus-backed CSE courses are NOT prefixed with the department
    assert "CSE 1105" not in degrees["BS-CS"].core_courses


def test_degree_loader_blocks_carry_credits_and_option_groups():
    """FC18: select-one requirement rows keep their option-group linkage.

    Creative Arts (BS-CS) has 8 options in the JSON — all must share a group.
    """
    degrees = {d.degree_id: d for d in load_degree_requirements(DATA_DIR)}
    blocks = {b.name: b for d in degrees.values() for b in d.blocks}
    creative = [b for b in blocks.values() if b.name.startswith("Creative Arts")][0]
    assert len(creative.courses) == 8
    assert len({c.option_group for c in creative.courses}) == 1
    assert creative.credits_required == 3


def test_degree_loader_elective_rules_from_bucket_rows():
    """FC18/FC32: elective buckets parse into name → credit-hour rules."""
    degrees = {d.degree_id: d for d in load_degree_requirements(DATA_DIR)}
    assert degrees["BS-CS"].elective_rules == {
        "CSE 4000-level Technical Electives": 12,
        "CSE 3000-level or 4000-level Technical Elective": 3,
    }
    assert degrees["BS-SE"].elective_rules == {
        "CSE 3000-level or 4000-level Technical Electives": 12,
    }


def test_derived_courses_include_non_cse_rows_with_hours():
    """FC33: gen-ed courses (ENGL 1301, MATH 1426) become course rows with the
    credit hours stated in the requirement tables — real data, not invented."""
    degrees = load_degree_requirements(DATA_DIR)
    courses = {c.course_id: c for c in derive_courses_from_requirements(degrees)}
    # CSE courses keep their normalized 4-digit id
    assert courses["1105"].credit_hours == 1
    assert courses["3330"].credit_hours == 3
    # Non-CSE courses are keyed by full code
    assert courses["ENGL 1301"].credit_hours == 3
    assert courses["ENGL 1301"].department == "ENGL"
    assert courses["MATH 1426"].credit_hours == 4
    assert courses["PHYS 1443"].credit_hours == 4


def test_catalog_documents_cover_general_core_and_certificate():
    """FC33: degree + catalog text (certificate, general core) becomes
    Chroma-side documents for semantic degree/requirement questions (FC22 fuel)."""
    docs = load_catalog_documents(DATA_DIR)
    ids = [doc["id"] for doc in docs]
    assert "catalog:AICertification" in ids
    assert "catalog:general-core" in ids
    assert "catalog:BS-CS" in ids
    assert "catalog:BS-SE" in ids
    for doc in docs:
        assert doc["text"].strip(), "empty catalog chunk would be fabricated filler"
        assert "kind" in doc["metadata"] and "source" in doc["metadata"]


# -------------------------------------------------- mock seed file integrity

def test_sections_mock_file_exists_and_is_labeled():
    """Mock sections must loudly announce they are demo data, not registrar data."""
    import json

    payload = json.loads((DATA_DIR / "sections-mock.json").read_text())
    assert "_comment" in payload
    assert "mock" in payload["_comment"].lower()
    assert isinstance(payload.get("sections"), list) and payload["sections"]


def test_sections_mock_course_ids_exist_in_corpus():
    """Grounded seed data: every mock section's course_id must exist in the
    real course corpus — no invented courses via the back door."""
    import json

    payload = json.loads((DATA_DIR / "sections-mock.json").read_text())
    corpus_ids = {c.course_id for c in load_course_desc(DATA_DIR)}
    for section in payload["sections"]:
        assert section["course_id"] in corpus_ids, section["course_id"]
        assert section["section_id"] and section["term"]
        assert section["meeting_days"] and section["instructor"]


def test_student_demo_file_matches_default_identity_and_fc21_statuses():
    """FC36/FC21: the demo profile targets the pre-auth fallback id and uses
    only FC21 statuses; major must match a real seeded degree major_name."""
    import json

    from database.seed import DEFAULT_STUDENT_ID
    from database.ingest.degree_requirements_loader import load_degree_requirements

    payload = json.loads((DATA_DIR / "student-demo.json").read_text())
    assert "mock" in payload.get("_comment", "").lower()
    student = payload["student"]
    assert student["student_id"] == DEFAULT_STUDENT_ID

    real_major_names = {d.major_name for d in load_degree_requirements(DATA_DIR)}
    assert student["current_major"] in real_major_names

    valid_statuses = {"not_taken", "in_progress", "taken", "passed", "failed"}
    for entry in payload["classes"]:
        assert entry["status"] in valid_statuses
        if entry["status"] in {"passed", "failed"}:
            assert entry.get("grade"), "graded status needs a grade"