from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import aiosqlite

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from theoria.providers import Message


def _get_db_path() -> Path:
    config_dir = Path.home() / ".config" / "theoria"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "sessions.db"


class SessionStorage:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or _get_db_path()
        self._connection: aiosqlite.Connection | None = None

    async def _get_connection(self) -> aiosqlite.Connection:
        if self._connection is None:
            self._connection = await aiosqlite.connect(self.db_path)
            await self._init_schema()
        return self._connection

    async def _init_schema(self) -> None:
        conn = self._connection
        if conn is None:
            return

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                state_json TEXT NOT NULL
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id)
        """)
        await conn.commit()

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()
            self._connection = None

    async def save_session(
        self,
        session_id: str,
        messages: list[Message],
        state: dict[str, Any],
        title: str | None = None,
    ) -> None:
        conn = await self._get_connection()
        now = datetime.now(UTC).isoformat()

        state_copy = {k: v for k, v in state.items() if k != "messages"}
        state_json = json.dumps(state_copy)

        if title is None:
            for msg in messages:
                if msg.role == "user":
                    title = msg.content[:50] + ("..." if len(msg.content) > 50 else "")
                    break
            title = title or "Untitled Session"

        cursor = await conn.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
        exists = await cursor.fetchone()

        if exists:
            await conn.execute(
                "UPDATE sessions SET title = ?, updated_at = ?, state_json = ? WHERE id = ?",
                (title, now, state_json, session_id),
            )
            await conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        else:
            insert_sql = (
                "INSERT INTO sessions (id, title, created_at, updated_at, state_json) "
                "VALUES (?, ?, ?, ?, ?)"
            )
            await conn.execute(insert_sql, (session_id, title, now, now, state_json))

        for msg in messages:
            await conn.execute(
                "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (session_id, msg.role, msg.content, now),
            )

        await conn.commit()

    async def load_session(
        self, session_id: str
    ) -> tuple[list[dict[str, str]], dict[str, Any]] | None:
        conn = await self._get_connection()

        cursor = await conn.execute("SELECT state_json FROM sessions WHERE id = ?", (session_id,))
        row = await cursor.fetchone()
        if not row:
            return None

        state: dict[str, Any] = json.loads(row[0])

        cursor = await conn.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id",
            (session_id,),
        )
        messages = [{"role": r[0], "content": r[1]} async for r in cursor]

        return messages, state

    async def list_sessions(self, limit: int = 20) -> AsyncIterator[dict[str, Any]]:
        conn = await self._get_connection()

        cursor = await conn.execute(
            """
            SELECT s.id, s.title, s.created_at, s.updated_at, COUNT(m.id) as message_count
            FROM sessions s
            LEFT JOIN messages m ON s.id = m.session_id
            GROUP BY s.id
            ORDER BY s.updated_at DESC
            LIMIT ?
            """,
            (limit,),
        )

        async for row in cursor:
            yield {
                "id": row[0],
                "title": row[1],
                "created_at": row[2],
                "updated_at": row[3],
                "message_count": row[4],
            }

    async def delete_session(self, session_id: str) -> bool:
        conn = await self._get_connection()

        cursor = await conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        await conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        await conn.commit()

        return cursor.rowcount > 0


def generate_session_id() -> str:
    return f"ses_{uuid4().hex[:12]}"
