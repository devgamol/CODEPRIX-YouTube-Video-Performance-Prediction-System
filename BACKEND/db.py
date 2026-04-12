import json
import sqlite3
from typing import Any, Dict, Optional

DB_FILE = "jobs.db"

conn = sqlite3.connect(DB_FILE, check_same_thread=False)
conn.row_factory = sqlite3.Row


def init_db() -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            status TEXT,
            progress TEXT,
            result TEXT
        )
        """
    )
    conn.commit()


def create_job(id: str) -> None:
    conn.execute(
        "INSERT INTO jobs (id, status, progress, result) VALUES (?, ?, ?, ?)",
        (id, "queued", "", ""),
    )
    conn.commit()


def update_job(
    id: str,
    status: Optional[str] = None,
    progress: Optional[str] = None,
    result: Optional[Any] = None,
) -> None:
    updates = {}

    if status is not None:
        updates["status"] = status
    if progress is not None:
        updates["progress"] = progress
    if result is not None:
        if isinstance(result, str):
            updates["result"] = result
        else:
            updates["result"] = json.dumps(result)

    if not updates:
        return

    set_clause = ", ".join(f"{field} = ?" for field in updates.keys())
    params = list(updates.values()) + [id]

    conn.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", params)
    conn.commit()


def get_job(id: str) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        "SELECT id, status, progress, result FROM jobs WHERE id = ?",
        (id,),
    ).fetchone()

    if row is None:
        return None

    parsed_result: Dict[str, Any] = {}
    if row["result"]:
        try:
            loaded = json.loads(row["result"])
            if isinstance(loaded, dict):
                parsed_result = loaded
            else:
                parsed_result = {"value": loaded}
        except json.JSONDecodeError:
            parsed_result = {}

    return {
        "id": row["id"],
        "status": row["status"],
        "progress": row["progress"],
        "result": parsed_result,
    }
