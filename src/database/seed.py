"""Seed pipeline (FC33/FC35): build/refresh SQLite + Chroma from data/.

Reload semantics (product decision): on every app startup the seed-owned
tables are refreshed from data/ (courses, requirements, sections, demo
student) and the Chroma collections are reset + re-ingested. User-owned
state — chat sessions/messages/pending actions and saved plans — persists
across restarts (FC34 is a requirement, not demo data).

Run manually:
    PYTHONPATH=src python -m database.seed
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from database.ingest.catalog_text_loader import load_catalog_documents
from database.ingest.course_desc_loader import load_course_desc
from database.ingest.degree_requirements_loader import (
    derive_courses_from_requirements,
    load_degree_requirements,
)
from database.ingest.demo_seed_loader import load_sections_mock, load_student_demo
from database.sql.sqlite_manager import SQLDatabaseManager
from database.vector.chroma_manager import (
    CATALOG_COLLECTION,
    COURSES_COLLECTION,
    VectorDatabaseManager,
)
from database.vector.embeddings import get_embedding_function

_logger = logging.getLogger("database.seed")

DEFAULT_STUDENT_ID = "STU-2026-9941"  # demo profile id == server's FC36 fallback

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def seed_sqlite(sql_manager: SQLDatabaseManager, data_dir: Path = DATA_DIR) -> None:
    """Refresh all seed-owned SQLite tables from data/ (courses → requirements → sections → student)."""
    sql_manager.connect()  # idempotent; applies migrations on fresh databases
    corpus = load_course_desc(data_dir)
    degrees = load_degree_requirements(data_dir)
    derived = derive_courses_from_requirements(degrees, corpus_ids={c.course_id for c in corpus})

    sql_manager.clear_seed_tables()

    # courses: corpus-backed rows first, then requirement-derived rows (non-CSE
    # + CSE courses missing from the corpus). Hours backfilled from requirement
    # tables — the only place the corpus lacks hours.
    corpus_ids = {c.course_id for c in corpus}
    for course in corpus:
        hours = next((d.credit_hours for d in derived if d.course_id == course.course_id and d.credit_hours), None)
        course.credit_hours = hours
        sql_manager.upsert_course(course, source="corpus")
    for course in derived:
        if course.course_id not in corpus_ids:
            sql_manager.upsert_course(course, source="requirements")

    # degrees + requirement rows (blocks, bucket rules)
    for degree in degrees:
        sql_manager.upsert_degree(degree, source_file=f"{degree.degree_id}.md")

    # mock sections (labeled demo data; validated against the course catalog)
    known_ids = corpus_ids | {c.course_id for c in derived}
    for section in load_sections_mock(data_dir):
        if section.course_id not in known_ids:
            raise ValueError(
                f"Mock section {section.section_id!r} references unknown course "
                f"{section.course_id!r} — mock seeds must not invent courses"
            )
        sql_manager.upsert_section(section)

    # demo student (one pre-auth account per FC36 baseline)
    demo = load_student_demo(data_dir)
    student = demo["student"]
    sql_manager.ensure_student(student["student_id"], name=student.get("name"))
    sql_manager.update_student_major(
        student["student_id"], student["current_major"], student.get("concentration"),
        record_history=False,  # initial major is not a change event (FC7 history starts empty)
    )
    sql_manager.set_selected_degree(student["student_id"], student.get("selected_degree_id") or "")
    sql_manager.update_profile_fields(
        student["student_id"],
        career_interest=student.get("career_interest"),
        include_summer_sessions=student.get("include_summer_sessions", False),
    )
    for entry in demo.get("classes", []):
        sql_manager.add_student_class(
            student["student_id"],
            entry["course_id"],
            status=entry["status"],
            bookmarked=entry.get("bookmarked", False),
            grade=entry.get("grade"),
            semester_taken=entry.get("semester_taken"),
        )
    for history_entry in reversed(demo.get("major_history", [])):
        sql_manager.append_major_history(
            student["student_id"],
            history_entry["major_name"],
            history_entry.get("concentration"),
            active=False,
        )
    _logger.info(
        "seed_sqlite: %d corpus + %d derived courses, %d degrees, %d sections, demo student %s",
        len(corpus), len([c for c in derived if c.course_id not in corpus_ids]), len(degrees),
        len(load_sections_mock(data_dir)), student["student_id"],
    )


def seed_chroma(vector_manager: VectorDatabaseManager, data_dir: Path = DATA_DIR) -> None:
    """Reload the unstructured corpus (reset + re-ingest per collection)."""
    vector_manager.reset(COURSES_COLLECTION)
    course_documents = [
        {
            "id": f"course:{course.course_id}",
            "text": f"{course.course_id} — {course.title}. {course.description or ''}".strip(),
            "metadata": {
                "course_id": course.course_id,
                "title": course.title,
                "description": course.description or "",
                "department": course.department,
                "credit_hours": course.credit_hours,
            },
        }
        for course in load_course_desc(data_dir)
    ]
    vector_manager.ingest_documents(COURSES_COLLECTION, course_documents)

    vector_manager.reset(CATALOG_COLLECTION)
    vector_manager.ingest_documents(CATALOG_COLLECTION, load_catalog_documents(data_dir))
    _logger.info(
        "seed_chroma: %d course docs, %d catalog docs", len(course_documents),
        len(load_catalog_documents(data_dir)),
    )


def run(
    sql_path: Optional[str] = None,
    chroma_path: Optional[str] = None,
    data_dir: Optional[Path] = None,
    embedding_mode: str = "hash",
) -> None:
    """CLI entry: build/refresh both stores (dev runs use 'hash' embeddings by
    default here; the server lifespan passes its configured mode)."""
    import os

    sql_path = sql_path or os.getenv("ADVISOR_SQLITE_PATH", "var/advisor.db")
    chroma_path = chroma_path or os.getenv("ADVISOR_CHROMA_PATH", "var/chroma")
    data_dir = data_dir or Path(os.getenv("ADVISOR_DATA_DIR", DATA_DIR))

    sql = SQLDatabaseManager(sql_path)
    sql.connect()
    seed_sqlite(sql, data_dir=data_dir)
    sql.disconnect()

    vector = VectorDatabaseManager(chroma_path, embedding_function=get_embedding_function(embedding_mode))
    vector.connect()
    seed_chroma(vector, data_dir=data_dir)
    vector.disconnect()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run(embedding_mode="hash")