"""Degree-plan persistence (FC4/FC6 groundwork + §4 save_degree_plan)."""
from __future__ import annotations

import json
import sqlite3
from typing import List, Optional

from core.entities.degree import DegreePlan
from database.errors import RecordNotFoundError


def save_degree_plan(conn: sqlite3.Connection, plan: DegreePlan) -> bool:
    """§4 contract (FC2 destination): store plan metadata + first version snapshot."""
    payload = plan.to_payload()
    conn.execute(
        """INSERT OR REPLACE INTO plans
               (plan_id, student_id, degree_id, target_major, concentration,
                includes_summer, is_active)
           VALUES (?, ?, ?, ?, ?, ?, 1)""",
        (plan.plan_id, plan.student_id, plan.degree_id, plan.target_major,
         plan.concentration, int(plan.includes_summer)),
    )
    conn.execute(
        "INSERT OR IGNORE INTO plan_versions (plan_id, version_number, payload, note) "
        "VALUES (?, 1, ?, 'initial generation')",
        (plan.plan_id, json.dumps(payload)),
    )
    conn.commit()
    return True


def create_plan_version(
    conn: sqlite3.Connection, plan_id: str, payload: dict, note: Optional[str] = None
) -> int:
    """FC4: next immutable version snapshot."""
    next_number = conn.execute(
        "SELECT COALESCE(MAX(version_number), 0) + 1 AS next FROM plan_versions WHERE plan_id = ?",
        (plan_id,),
    ).fetchone()["next"]
    _require_plan_exists(conn, plan_id)
    conn.execute(
        "INSERT INTO plan_versions (plan_id, version_number, payload, note) VALUES (?, ?, ?, ?)",
        (plan_id, next_number, json.dumps(payload), note),
    )
    conn.commit()
    return next_number


def list_plans(conn: sqlite3.Connection, student_id: str) -> List[dict]:
    """FC6: all of the student's plans."""
    rows = conn.execute(
        "SELECT * FROM plans WHERE student_id = ? ORDER BY created_at, plan_id",
        (student_id,),
    ).fetchall()
    return [_row_to_plan_dict(conn, r) for r in rows]


def get_plan(conn: sqlite3.Connection, student_id: str, plan_id: str) -> Optional[dict]:
    row = conn.execute(
        "SELECT * FROM plans WHERE plan_id = ? AND student_id = ?", (plan_id, student_id)
    ).fetchone()
    if row is None:
        raise RecordNotFoundError(f"Plan {plan_id!r} not found for student {student_id!r}")
    return _row_to_plan_dict(conn, row)


def list_plan_versions(conn: sqlite3.Connection, plan_id: str) -> List[dict]:
    """FC4: version history, oldest first."""
    _require_plan_exists(conn, plan_id)
    rows = conn.execute(
        "SELECT version_number, payload, note, created_at FROM plan_versions "
        "WHERE plan_id = ? ORDER BY version_number",
        (plan_id,),
    ).fetchall()
    return [
        {
            "version_number": r["version_number"],
            "payload": json.loads(r["payload"]),
            "note": r["note"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def _require_plan_exists(conn: sqlite3.Connection, plan_id: str) -> dict:
    row = conn.execute(
        "SELECT student_id, target_major, concentration, includes_summer "
        "FROM plans WHERE plan_id = ?",
        (plan_id,),
    ).fetchone()
    if row is None:
        raise RecordNotFoundError(f"Plan {plan_id!r} not found")
    return dict(row)


def _row_to_plan_dict(conn: sqlite3.Connection, row: sqlite3.Row) -> dict:
    versions = conn.execute(
        "SELECT version_number, payload FROM plan_versions WHERE plan_id = ? ORDER BY version_number",
        (row["plan_id"],),
    ).fetchall()
    payload = json.loads(versions[-1]["payload"]) if versions else {"semesters": []}
    return {
        "plan_id": row["plan_id"],
        "student_id": row["student_id"],
        "degree_id": row["degree_id"],
        "target_major": row["target_major"],
        "concentration": row["concentration"],
        "includes_summer": bool(row["includes_summer"]),
        "created_at": row["created_at"],
        "version_number": versions[-1]["version_number"] if versions else 0,
        "semesters": payload.get("semesters", []),
    }