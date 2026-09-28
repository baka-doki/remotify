import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(os.getenv("REMOTIFY_DB_PATH", "data/remotify.db"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                openai_conversation_id TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                model TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(conversation_id) REFERENCES conversations(id)
            );

            CREATE INDEX IF NOT EXISTS idx_messages_conversation
            ON messages(conversation_id, id);
            """
        )


def create_conversation(openai_conversation_id: str, model: str) -> dict:
    local_id = uuid.uuid4().hex
    now = _now()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO conversations
            (id, openai_conversation_id, title, model, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (local_id, openai_conversation_id, "New chat", model, now, now),
        )
    return get_conversation(local_id)


def list_conversations() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, title, model, created_at, updated_at
            FROM conversations
            ORDER BY updated_at DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_conversation(conversation_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
    return dict(row) if row else None


def get_messages(conversation_id: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, role, content, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
            """,
            (conversation_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def add_message(conversation_id: str, role: str, content: str) -> None:
    now = _now()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO messages (conversation_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (conversation_id, role, content, now),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conversation_id),
        )


def maybe_set_title(conversation_id: str, first_user_text: str) -> None:
    title = " ".join(first_user_text.strip().split())[:48] or "New chat"
    with _connect() as conn:
        row = conn.execute(
            "SELECT title FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
        if row and row["title"] == "New chat":
            conn.execute(
                "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
                (title, _now(), conversation_id),
            )
