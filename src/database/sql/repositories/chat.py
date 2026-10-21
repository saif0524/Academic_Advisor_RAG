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
    row = conn.execute(
        "SELECT student_id FROM chat_sessions WHERE session_id = ?", (session_id,)
    ).fetchone()
    if row is None or row["student_id"] != student_id:
        raise RecordNotFoundError(f"Chat session {session_id!r} not found for student {student_id!r}")
    rows = conn.execute(
        "SELECT role, content, created_at FROM chat_messages WHERE session_id = ? ORDER BY id",
        (session_id,),
    ).fetchall()
    return [dict(r) for r in rows]


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
        "SELECT action_id, session_id, action_type, description, payload, status, created_at "
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