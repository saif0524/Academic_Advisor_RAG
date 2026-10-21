"""Degree-catalog queries (FC15/FC16/FC18 + FC32 caps) — reads for services,
upserts for the seed pipeline."""
from __future__ import annotations

import sqlite3
from typing import List, Optional

from core.entities.degree import DegreeBlock, DegreeBlockCourse, DegreeRequirement


def list_degrees(conn: sqlite3.Connection) -> List[DegreeRequirement]:
    """FC15: every ingested degree record (no invented rows)."""
    rows = conn.execute("SELECT * FROM degrees ORDER BY degree_id").fetchall()
    return [_rows_to_degree(conn, r) for r in rows]


def get_degree(conn: sqlite3.Connection, degree_id: str) -> Optional[DegreeRequirement]:
    row = conn.execute("SELECT * FROM degrees WHERE degree_id = ?", (degree_id,)).fetchone()
    return _rows_to_degree(conn, row) if row else None


def get_degree_requirement_rows(conn: sqlite3.Connection, degree_id: str) -> List[dict]:
    """FC19 fuel: block-level rows for deterministic progress counting."""
    blocks = conn.execute(
        "SELECT id, block_name, kind, credits_required, elective_bucket "
        "FROM degree_requirement_blocks WHERE degree_id = ? ORDER BY sort_order, id",
        (degree_id,),
    ).fetchall()
    out: List[dict] = []
    for block in blocks:
        courses = conn.execute(
            "SELECT course_code, course_id, title, credit_hours, option_group "
            "FROM degree_requirement_courses WHERE block_id = ? ORDER BY id",
            (block["id"],),
        ).fetchall()
        out.append(
            {
                "block_id": block["id"],
                "block_name": block["block_name"],
                "kind": block["kind"],
                "credits_required": block["credits_required"],
                "elective_bucket": block["elective_bucket"],
                "courses": [dict(c) for c in courses],
            }
        )
    return out


def upsert_degree(
    conn: sqlite3.Connection, degree: DegreeRequirement, source_file: str
) -> None:
    """Seed-side write (FC33): degree + all block/requirement rows.

    Idempotent full replace per degree (reload semantics).
    """
    conn.execute(
        """INSERT OR REPLACE INTO degrees
               (degree_id, major_name, total_credits_required, max_semester_credits,
                institution, source_file)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            degree.degree_id, degree.major_name, degree.total_credits_required,
            degree.max_semester_credits, degree.institution, source_file,
        ),
    )
    conn.execute("DELETE FROM degree_requirement_courses WHERE degree_id = ?", (degree.degree_id,))
    conn.execute("DELETE FROM degree_requirement_blocks WHERE degree_id = ?", (degree.degree_id,))
    for order, block in enumerate(degree.blocks):
        conn.execute(
            """INSERT INTO degree_requirement_blocks
                   (degree_id, block_name, kind, credits_required, elective_bucket, sort_order)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (degree.degree_id, block.name, block.kind, block.credits_required,
             block.elective_bucket, order),
        )
        block_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        for row in block.courses:
            conn.execute(
                """INSERT INTO degree_requirement_courses
                       (degree_id, block_id, course_code, course_id, title, credit_hours, option_group)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (degree.degree_id, block_id, row.course_code, row.course_id,
                 row.title, row.credit_hours, row.option_group),
            )


def _rows_to_degree(conn: sqlite3.Connection, row: sqlite3.Row) -> DegreeRequirement:
    degree_id = row["degree_id"]
    block_rows = get_degree_requirement_rows(conn, degree_id)
    blocks = [
        DegreeBlock(
            name=b["block_name"], kind=b["kind"], credits_required=b["credits_required"],
            elective_bucket=b["elective_bucket"],
            courses=[
                DegreeBlockCourse(
                    course_code=c["course_code"], title=c["title"], credit_hours=c["credit_hours"],
                    course_id=c["course_id"], option_group=c["option_group"],
                )
                for c in b["courses"]
            ],
        )
        for b in block_rows
    ]
    core_ids, concentration_ids, elective_rules = _split_degree_fields(blocks)
    return DegreeRequirement(
        degree_id=degree_id,
        major_name=row["major_name"],
        total_credits_required=row["total_credits_required"],
        max_semester_credits=row["max_semester_credits"],
        core_courses=core_ids,
        concentration_courses=concentration_ids,
        elective_rules=elective_rules,
        blocks=blocks,
    )


def _split_degree_fields(blocks: List[DegreeBlock]):
    """Derive §1 lists from block rows: core = major_core rows;
    electives = bucket blocks (bucket name → credit hours)."""
    core: List[str] = []
    concentration: List[str] = []
    rules: dict = {}
    for block in blocks:
        if block.kind == "major_core":
            core.extend(_course_ids(block))
        elif block.kind == "concentration":
            concentration.extend(_course_ids(block))
        elif block.kind == "electives" and block.elective_bucket:
            rules[block.elective_bucket] = block.credits_required or 0
    return core, concentration, rules


def _course_ids(block: DegreeBlock) -> List[str]:
    return [row.course_id or row.course_code for row in block.courses if row.course_id or row.course_code]