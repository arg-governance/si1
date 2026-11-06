"""SQL-based logging implementation for SI-1 dual-log (JSONL + SQL database).

Provides SQLLogger and SQLDuelLog classes that mirror the functionality of
the existing JSONL-based Logger and DuelLog, but store data in SQLite databases
for enhanced querying capabilities while maintaining the JSONL files for
backward compatibility and audit trails.
"""

from __future__ import annotations

import asyncio
import json
import time
import sqlite3
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Optional

import aiofiles
import aiosqlite

import config
import models as M


# Detail keys whose values are treated as potentially-sensitive content
# (full prompts, context blocks, user-supplied freeform text). When present,
# the value is replaced by a length marker so the log stays small and free
# of accidental PII / IP leaks. Add more keys here as needed.
_REDACT_KEYS: frozenset[str] = frozenset({
    "prompt",
    "system_prompt",
    "context_block",
    "user_input",
    "input",
    "output",
    "proposed",
    "msg",
    "raw",
})


def _redact(detail: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow copy of *detail* with sensitive values replaced by
    a length marker. Non-string values for sensitive keys are also redacted
    because we never want raw model responses or prompts landing in the log.
    """
    out: dict[str, Any] = {}
    for k, v in detail.items():
        if k in _REDACT_KEYS:
            if isinstance(v, str):
                out[k] = f"<redacted len={len(v)}>"
            else:
                out[k] = f"<redacted type={type(v).__name__}>"
        else:
            out[k] = v
    return out


@dataclass
class SQLRunLogEvent:
    """Represents a runtime log event for SQL storage."""
    ts: float
    event: str
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class SQLDuelLogEvent:
    """Represents a duel log event for SQL storage."""
    ts: int
    turn: int
    round: int
    kind: str
    actor: str
    text: str
    meta: dict[str, Any] = field(default_factory=dict)


class SQLLogger:
    """
    Async SQLite-based execution logger that mirrors JSONL Logger functionality.

    Stores logs in SQLite database for enhanced querying while maintaining
    the existing JSONL file for backward compatibility.
    """

    def __init__(self,
                 log_file: Path = config.RUN_LOG_FILE,
                 db_file: Optional[Path] = None) -> None:
        self.log_file = log_file  # Keep JSONL for backward compatibility
        self.db_file = db_file or (log_file.parent / f"{log_file.stem}.db")
        self._lock = asyncio.Lock()
        self._initialized = False

    async def _initialize_db(self) -> None:
        """Initialize the SQLite database with required tables."""
        if self._initialized:
            return

        async with aiosqlite.connect(self.db_file) as db:
            # Create run_log table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS run_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    event TEXT NOT NULL,
                    detail JSON NOT NULL
                )
            """)

            # Create index on timestamp for efficient time-based queries
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_run_log_ts ON run_log(ts)
            """)

            # Create index on event type for filtering
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_run_log_event ON run_log(event)
            """)

            await db.commit()

        self._initialized = True

    async def log(self, event: str, **detail: Any) -> None:
        """Log an event to both JSONL file and SQL database."""
        # Redact sensitive details
        redacted_detail = _redact(detail)

        # Create log event
        evt = SQLRunLogEvent(
            ts=time.time(),
            event=event,
            detail=redacted_detail,
        )

        # Write to JSONL file (maintain backward compatibility)
        await self._append_to_jsonl(evt)

        # Write to SQL database
        await self._append_to_sql(evt)

    async def log_failure(self, event: str, error: BaseException, **detail: Any) -> None:
        """Log a failure event to both JSONL file and SQL database."""
        # Redact sensitive details and add error info
        redacted_detail = _redact({**detail, "error": repr(error)})

        # Create log event
        evt = SQLRunLogEvent(
            ts=time.time(),
            event=event,
            detail=redacted_detail,
        )

        # Write to JSONL file (maintain backward compatibility)
        await self._append_to_jsonl(evt)

        # Write to SQL database
        await self._append_to_sql(evt)

    async def _append_to_jsonl(self, evt: SQLRunLogEvent) -> None:
        """Append event to JSONL file (backward compatibility)."""
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(asdict(evt), ensure_ascii=False, separators=(",", ":"))

        async with aiofiles.open(self.log_file, "a", encoding="utf-8") as f:
            await f.write(line + "\n")

    async def _append_to_sql(self, evt: SQLRunLogEvent) -> None:
        """Append event to SQL database."""
        # Ensure database is initialized
        await self._initialize_db()

        # Insert into database
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute(
                """
                INSERT INTO run_log (ts, event, detail)
                VALUES (?, ?, ?)
                """,
                (evt.ts, evt.event, json.dumps(evt.detail, ensure_ascii=False))
            )
            await db.commit()

    async def query_recent_events(self, limit: int = 10) -> list[dict[str, Any]]:
        """Return the newest run-log events from the SQLite database."""
        await self._initialize_db()
        async with aiosqlite.connect(self.db_file) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT * FROM run_log
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]


class SQLDuelLog:
    """Async SQLite-based duel log that mirrors JSONL DuelLog functionality.

    Stores duel logs in SQLite database for enhanced querying while maintaining
    the existing JSONL file as the auditor's source of truth.
    """

    def __init__(self,
                 log_file: Path = config.DUEL_LOG_FILE,
                 db_file: Optional[Path] = None) -> None:
        self.log_file = log_file  # Keep JSONL as auditor's source of truth
        self.db_file = db_file or (log_file.parent / f"{log_file.stem}.db")
        self._lock = asyncio.Lock()
        self._initialized = False

    async def _initialize_db(self) -> None:
        """Initialize the SQLite database with required tables."""
        if self._initialized:
            return

        async with aiosqlite.connect(self.db_file) as db:
            # Create duel_log table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS duel_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts INTEGER NOT NULL,
                    turn INTEGER NOT NULL,
                    round INTEGER NOT NULL,
                    kind TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    text TEXT NOT NULL,
                    meta JSON NOT NULL
                )
            """)

            # Create indexes for common query patterns
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_duel_log_turn ON duel_log(turn)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_duel_log_kind ON duel_log(kind)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_duel_log_actor ON duel_log(actor)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_duel_log_ts ON duel_log(ts)
            """)

            # Composite index for common turn+kind queries
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_duel_log_turn_kind ON duel_log(turn, kind)
            """)

            await db.commit()

        self._initialized = True

    async def record(
        self,
        turn: int,
        round: int,
        kind: str,
        actor: str,
        text: str,
        **meta: Any,
    ) -> None:
        """Record a duel event to both JSONL file and SQL database."""
        # Create duel log entry
        entry = SQLDuelLogEvent(
            ts=int(time.time()),
            turn=turn,
            round=round,
            kind=kind,
            actor=actor,
            text=text or "",
            meta=dict(meta),
        )

        # Write to JSONL file (maintain auditor's source of truth)
        await self._append_to_jsonl(entry)

        # Write to SQL database
        await self._append_to_sql(entry)

    async def _append_to_jsonl(self, entry: SQLDuelLogEvent) -> None:
        """Append entry to JSONL file (auditor's source of truth)."""
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(asdict(entry), ensure_ascii=False, separators=(",", ":"))

        async with aiofiles.open(self.log_file, "a", encoding="utf-8") as f:
            await f.write(line + "\n")

    async def _append_to_sql(self, entry: SQLDuelLogEvent) -> None:
        """Append entry to SQL database."""
        # Ensure database is initialized
        await self._initialize_db()

        # Insert into database
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute(
                """
                INSERT INTO duel_log (ts, turn, round, kind, actor, text, meta)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.ts,
                    entry.turn,
                    entry.round,
                    entry.kind,
                    entry.actor,
                    entry.text,
                    json.dumps(entry.meta, ensure_ascii=False)
                )
            )
            await db.commit()

    # Additional query methods for enhanced SQL functionality

    async def query_recent_turns(self, limit: int = 10) -> list[dict[str, Any]]:
        """Query recent duel log entries by turn number."""
        await self._initialize_db()

        async with aiosqlite.connect(self.db_file) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT * FROM duel_log
                ORDER BY turn DESC, round DESC
                LIMIT ?
                """,
                (limit,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def query_by_kind(self, kind: str, limit: int = 100) -> list[dict[str, Any]]:
        """Query duel log entries by kind (e.g., 'gate', 'critique')."""
        await self._initialize_db()

        async with aiosqlite.connect(self.db_file) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT * FROM duel_log
                WHERE kind = ?
                ORDER BY turn DESC, round DESC
                LIMIT ?
                """,
                (kind, limit)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def query_by_turn(self, turn: int) -> list[dict[str, Any]]:
        """Query all duel log entries for a specific turn."""
        await self._initialize_db()

        async with aiosqlite.connect(self.db_file) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT * FROM duel_log
                WHERE turn = ?
                ORDER BY round ASC
                """,
                (turn,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_turn_summary(self, turn: int) -> dict[str, Any]:
        """Get a summary of events for a specific turn."""
        await self._initialize_db()

        async with aiosqlite.connect(self.db_file) as db:
            # Get counts by kind
            async with db.execute(
                """
                SELECT kind, COUNT(*) as count
                FROM duel_log
                WHERE turn = ?
                GROUP BY kind
                """,
                (turn,)
            ) as cursor:
                kind_counts = {row[0]: row[1] for row in await cursor.fetchall()}

            # Get gate verdict if exists
            async with db.execute(
                """
                SELECT accepted, reason
                FROM duel_log
                WHERE turn = ? AND kind = 'gate'
                ORDER BY round DESC
                LIMIT 1
                """,
                (turn,)
            ) as cursor:
                gate_row = await cursor.fetchone()
                gate_verdict = {
                    "accepted": bool(gate_row[0]) if gate_row else None,
                    "reason": gate_row[1] if gate_row else None
                } if gate_row else None

            return {
                "turn": turn,
                "kind_counts": kind_counts,
                "gate_verdict": gate_verdict
            }