from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from config import get_settings

Message = dict[str, str]

logger = logging.getLogger(__name__)

MAX_HISTORY_MESSAGES = 20
# How many recent turns to show when the user opens the bot again.
MAX_DISPLAY_MESSAGES = 10
TELEGRAM_MESSAGE_LIMIT = 4096


def _db_path() -> str:
    return get_settings().conversations_db


def _connect(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or _db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str | None = None) -> None:
    path = db_path or _db_path()
    with _connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages (chat_id, id)"
        )
        conn.commit()
    logger.info(
        "database initialized",
        extra={"event": "db_init", "db_path": path},
    )


def load_history(chat_id: int, limit: int = MAX_HISTORY_MESSAGES) -> list[Message]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT role, content
            FROM (
                SELECT role, content, id
                FROM messages
                WHERE chat_id = ?
                ORDER BY id DESC
                LIMIT ?
            )
            ORDER BY id ASC
            """,
            (chat_id, limit),
        ).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in rows]


def append_message(chat_id: int, role: str, content: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO messages (chat_id, role, content) VALUES (?, ?, ?)",
            (chat_id, role, content),
        )
        conn.commit()
        excess = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE chat_id = ?",
            (chat_id,),
        ).fetchone()[0]
        if excess > MAX_HISTORY_MESSAGES:
            conn.execute(
                """
                DELETE FROM messages
                WHERE chat_id = ? AND id NOT IN (
                    SELECT id FROM messages
                    WHERE chat_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                )
                """,
                (chat_id, chat_id, MAX_HISTORY_MESSAGES),
            )
            conn.commit()


def clear_history(chat_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        conn.commit()
    logger.info(
        "conversation cleared",
        extra={"event": "conversation_reset", "chat_id": chat_id},
    )


def remove_last_message(chat_id: int) -> None:
    with _connect() as conn:
        conn.execute(
            """
            DELETE FROM messages
            WHERE id = (
                SELECT id FROM messages
                WHERE chat_id = ?
                ORDER BY id DESC
                LIMIT 1
            )
            """,
            (chat_id,),
        )
        conn.commit()


def format_history_for_display(
    messages: list[Message],
    *,
    limit: int = MAX_DISPLAY_MESSAGES,
) -> str:
    if not messages:
        return ""

    recent = messages[-limit:]
    lines: list[str] = ["История вашего диалога:\n"]
    for msg in recent:
        label = "Вы" if msg["role"] == "user" else "Ассистент"
        lines.append(f"{label}: {msg['content']}\n")

    text = "\n".join(lines).strip()
    if len(text) <= TELEGRAM_MESSAGE_LIMIT:
        return text

    truncated = text[: TELEGRAM_MESSAGE_LIMIT - 50].rsplit("\n", 1)[0]
    return truncated + "\n\n… (показана часть истории)"
