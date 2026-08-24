from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Optional

import aiofiles

import config
from models import RuntimeState, Fact, ArchiveEntry


class MemoryStore:
    """
    Async JSON persistence for runtime state, facts, and archive.

    - load() reads three JSON files concurrently
    - save() writes three JSON files concurrently
    - Files use compact formatting on disk to stay diff-friendly
    """

    def __init__(
        self,
        runtime_file: Path = config.RUNTIME_FILE,
        facts_file: Path = config.FACTS_FILE,
        archive_file: Path = config.ARCHIVE_FILE,
    ) -> None:
        self.runtime_file = runtime_file
        self.facts_file = facts_file
        self.archive_file = archive_file

    # ------------------------------------------------------------------ load
    async def load(self) -> tuple[RuntimeState, list[Fact], list[ArchiveEntry]]:
        # ``return_exceptions=True`` so one unreadable file (e.g. a
        # truncated facts.json from a previous crash) cannot abort the
        # whole boot. The three loads are independent — we treat a None
        # for a failed load as "no data for this file" rather than dying.
        results = await asyncio.gather(
            self._load_json(self.runtime_file),
            self._load_json(self.facts_file),
            self._load_json(self.archive_file),
            return_exceptions=True,
        )
        runtime_raw, facts_raw, archive_raw = (
            r if not isinstance(r, BaseException) else None for r in results
        )
        return (
            RuntimeState.from_dict(runtime_raw),
            self._parse_facts(facts_raw),
            self._parse_archive(archive_raw),
        )

    # ------------------------------------------------------------------ save
    async def save(
        self,
        runtime: RuntimeState,
        facts: list[Fact],
        archive: list[ArchiveEntry],
    ) -> None:
        # Same isolation rationale as ``load``: a failure writing the
        # archive must not lose the runtime counter / facts update.
        # Exceptions are logged and swallowed at the call site instead.
        await asyncio.gather(
            self._save_json(self.runtime_file, runtime.to_dict()),
            self._save_json(self.facts_file, [f.to_dict() for f in facts]),
            self._save_json(self.archive_file, [a.to_dict() for a in archive]),
            return_exceptions=True,
        )

    # --------------------------------------------------------------- helpers
    @staticmethod
    async def _load_json(path: Path) -> Any:
        if not path.exists():
            return None
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            text = await f.read()
        if not text.strip():
            return None
        return json.loads(text)

    @staticmethod
    async def _save_json(path: Path, data: Any, *, compact: bool = True) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if compact:
            payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        else:
            payload = json.dumps(data, ensure_ascii=False, indent=2)
        async with aiofiles.open(path, "w", encoding="utf-8") as f:
            await f.write(payload)

    @staticmethod
    def _parse_facts(raw: Any) -> list[Fact]:
        if not isinstance(raw, list):
            return []
        out: list[Fact] = []
        for item in raw:
            if isinstance(item, dict):
                out.append(Fact.from_dict(item))
        return out

    @staticmethod
    def _parse_archive(raw: Any) -> list[ArchiveEntry]:
        if not isinstance(raw, list):
            return []
        out: list[ArchiveEntry] = []
        for item in raw:
            if isinstance(item, dict):
                out.append(ArchiveEntry.from_dict(item))
        return out