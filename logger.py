from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

import aiofiles

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
class RunLogEvent:
    ts: float
    event: str
    detail: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, separators=(",", ":"))


class Logger:
    """
    Async append-only JSONL execution logger.

    - log() / log_failure() are awaitable
    - File is opened once per write (aiofiles handles append safely)
    - Serial writes are gated by an asyncio.Lock to avoid interleaving
      when multiple coroutines log concurrently
    - Detail values whose keys match _REDACT_KEYS are replaced with a
      length marker before being written, so the log never embeds full
      prompts, user inputs, or model outputs.
    """

    def __init__(self, log_file: Path = config.RUN_LOG_FILE) -> None:
        self.log_file = log_file
        self._lock = asyncio.Lock()

    async def log(self, event: str, **detail: Any) -> None:
        evt = RunLogEvent(
            ts=time.time(),
            event=event,
            detail=_redact(detail),
        )
        await self._append(evt.to_json())

    async def log_failure(self, event: str, error: BaseException, **detail: Any) -> None:
        evt = RunLogEvent(
            ts=time.time(),
            event=event,
            detail=_redact({**detail, "error": repr(error)}),
        )
        await self._append(evt.to_json())

    async def _append(self, line: str) -> None:
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        async with self._lock:
            async with aiofiles.open(self.log_file, "a", encoding="utf-8") as f:
                await f.write(line + "\n")


class DuelLog:
    """Async content log for the four-phase duel loop.

    Writes to ``config.DUEL_LOG_FILE`` (default: ./logs/duellog.json) using
    JSONL semantics: one JSON object per line, appended in arrival order.
    The file extension is .json but each line is a self-contained record.

    Unlike ``Logger``, this log does NOT redact values — it is the auditor's
    source of truth for what was actually said during a duel round. Only the
    runtime process can read it, and it lives behind the Architect's
    filesystem permissions.

    ``record()`` is the single entry point. Pass:
        - turn:  SI-1 monotonic turn counter (from RuntimeState)
        - round: 0 for the initial draft, 1+ for revise rounds
        - kind:  'draft' | 'critique' | 'mutation' | 'gate' | 'rejection'
        - actor: 'lucifer' | 'obi' | 'runtime'
        - text:  the actual content
        - meta:  any extra metadata (score, elapsed, gate reason, ...)
    """

    def __init__(self, log_file: Path = config.DUEL_LOG_FILE) -> None:
        self.log_file = Path(log_file)
        self._lock = asyncio.Lock()

    async def record(
        self,
        turn: int,
        round: int,
        kind: str,
        actor: str,
        text: str,
        **meta: Any,
    ) -> None:
        entry = M.DuelLogEntry(
            ts=int(time.time()),
            turn=turn,
            round=round,
            kind=kind,
            actor=actor,
            text=text or "",
            meta=dict(meta),
        )
        line = json.dumps(entry.to_dict(), ensure_ascii=False, separators=(",", ":"))
        await self._append(line)

    async def _append(self, line: str) -> None:
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        async with self._lock:
            async with aiofiles.open(self.log_file, "a", encoding="utf-8") as f:
                await f.write(line + "\n")