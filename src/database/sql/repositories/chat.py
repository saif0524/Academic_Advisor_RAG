"""Chat/advising persistence (FC34) + FC23 pending-action groundwork."""
from __future__ import annotations

import json
import sqlite3
import uuid
from typing import List, Optional

from database.errors import RecordNotFoundError


def ensure_chat_session(conn: sqlite3.Connection, student_id: str) -> str:
    """FC27/FC34: reuse the student's active session, or open one."""
    row = conn.execute(
        "SELECT session_id FROM chat_sessions WHERE student_id = ? ORDER BY last_active_at DESC LIMIT 1",
        (student_id,),
    ).fetchone()
    if row is not None:
        session_id = row["session_id"]
    else:
        session_id = f"sess-{uuid.uuid4()}"
        conn.execute("INSERT INTO chat_sessions (session_id, student_id) VALUES (?, ?)", (session_id, student_id))
        conn.commit()
    conn.execute(
        "UPDATE chat_sessions SET last_active_at = CURRENT_TIMESTAMP WHERE session_id = ?",
        (session_id,),
    )
    conn.commit()
    return session_id


def append_chat_message(
    conn: sqlite3.Connection, session_id: str, student_id: str, role: str, content: str
) -> None:
    """FC34: persist one turn (role: 'user' | 'assistant')."""
    if role not in {"user", "assistant"}:
        raise ValueError(f"Invalid chat role {role!r}")
    conn.execute(
        "INSERT INTO chat_messages (session_id, student_id, role, content) VALUES (?, ?, ?, ?)",
        (session_id, student_id, role, content),
    )
    conn.execute(
        "UPDATE chat_sessions SET last_active_at = CURRENT_TIMESTAMP WHERE session_id = ?",
        (session_id,),
    )
    conn.commit()


def get_chat_history(conn: sqlite3.Connection, student_id: str, session_id: str) -> List[dict]:
    """FC34: persisted turns oldest-first; unknown session → honest 404."""
    if not session_exists(conn, student_id, session_id):
        raise RecordNotFoundError(
            f"Chat session {session_id!r} not found for student {student_id!r}")
    rows = conn.execute(
        "SELECT role, content, created_at FROM chat_messages WHERE session_id = ? ORDER BY id",
        (session_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def session_exists(conn: sqlite3.Connection, student_id: str, session_id: str) -> bool:
    """FC34: ownership check — the session must exist AND belong to the student."""
    row = conn.execute(
        "SELECT student_id FROM chat_sessions WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    return row is not None and row["student_id"] == student_id


def get_open_pending_action(conn: sqlite3.Connection, session_id: str) -> Optional[dict]:
    """FC23 durability: the session's newest OPEN proposal (server-side gate
    state) — history reads surface it so the UI card survives reloads."""
    row = conn.execute(
        "SELECT action_id, action_type, description FROM chat_pending_actions"
        " WHERE session_id = ? AND status = 'open' ORDER BY created_at DESC, rowid DESC LIMIT 1",
        (session_id,),
    ).fetchone()
    return dict(row) if row else None


def list_chat_sessions(conn: sqlite3.Connection, student_id: str) -> List[dict]:
    """FC34/FC35 view: the student's sessions, newest activity first. The
    title is the first user message (truncated), never a fabricated title."""
    rows = conn.execute(
        """SELECT s.session_id, s.created_at, s.last_active_at,
                  (SELECT SUBSTR(m.content, 1, 80) FROM chat_messages m
                   WHERE m.session_id = s.session_id AND m.role = 'user'
                   ORDER BY m.id LIMIT 1) AS title
           FROM chat_sessions s
           WHERE s.student_id = ?
           ORDER BY s.last_active_at DESC""",
        (student_id,),
    ).fetchall()
    return [
        {
            "session_id": row["session_id"],
            "title": row["title"] or "(no messages yet)",
            "created_at": row["created_at"],
            "last_active_at": row["last_active_at"],
        }
        for row in rows
    ]


# --------------------------------------------------------- FC23 groundwork

def create_pending_action(
    conn: sqlite3.Connection, session_id: str, student_id: str,
    action_type: str, description: str, payload: dict,
) -> str:
    """FC23: a proposed action survives restarts so the confirmation card and
    chat flow can resume it later."""
    action_id = f"act-{uuid.uuid4()}"
    conn.execute(
        """INSERT INTO chat_pending_actions (action_id, session_id, student_id, action_type, description, payload)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (action_id, session_id, student_id, action_type, description, json.dumps(payload)),
    )
    conn.commit()
    return action_id


def get_pending_action(conn: sqlite3.Connection, action_id: str) -> Optional[dict]:
    row = conn.execute(
        "SELECT action_id, session_id, student_id, action_type, description, payload, status, created_at "
        "FROM chat_pending_actions WHERE action_id = ?",
        (action_id,),
    ).fetchone()
    if row is None:
        return None
    result = dict(row)
    result["payload"] = json.loads(result["payload"])
    return result


def resolve_pending_action(conn: sqlite3.Connection, action_id: str, status: str) -> bool:
    """FC23: 'confirmed' | 'cancelled'; returns False for unknown action ids."""
    if status not in {"confirmed", "cancelled"}:
        raise ValueError(f"Invalid pending-action status {status!r}")
    cursor = conn.execute(
        "UPDATE chat_pending_actions SET status = ?, resolved_at = CURRENT_TIMESTAMP "
        "WHERE action_id = ? AND status = 'open'",
        (status, action_id),
    )
    conn.commit()
    return cursor.rowcount > 0