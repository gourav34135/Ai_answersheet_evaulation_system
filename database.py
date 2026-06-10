import json
import sqlite3
from datetime import datetime
from typing import Any

from config import DATABASE_PATH, DATA_DIR


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_name TEXT NOT NULL,
                question TEXT,
                reference_answer TEXT,
                marking_points TEXT,
                file_name TEXT NOT NULL,
                extracted_text TEXT NOT NULL,
                score REAL NOT NULL,
                max_score REAL NOT NULL,
                confidence TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def save_evaluation(payload: dict[str, Any]) -> int:
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO evaluations (
                student_name,
                question,
                reference_answer,
                marking_points,
                file_name,
                extracted_text,
                score,
                max_score,
                confidence,
                result_json,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["student_name"],
                payload.get("question", ""),
                payload.get("reference_answer", ""),
                payload.get("marking_points", ""),
                payload["file_name"],
                payload["extracted_text"],
                payload["score"],
                payload["max_score"],
                payload["confidence"],
                json.dumps(payload["result"], ensure_ascii=True),
                created_at,
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def list_evaluations(limit: int = 25) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, student_name, file_name, score, max_score, confidence, created_at
            FROM evaluations
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_evaluation(evaluation_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM evaluations WHERE id = ?",
            (evaluation_id,),
        ).fetchone()
    if row is None:
        return None

    item = dict(row)
    item["result"] = json.loads(item.pop("result_json"))
    return item


def delete_evaluation(evaluation_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM evaluations WHERE id = ?", (evaluation_id,))
        conn.commit()
        return cursor.rowcount > 0


def clear_history() -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM evaluations")
        conn.commit()
