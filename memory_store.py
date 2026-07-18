"""Persistent JSON memory storage for SI-1 with structural type safety."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from config import ARCHIVE_FILE, FACTS_FILE, MEMORY_DIR, RUNTIME_FILE
from logger import Logger
from models import MemorySnapshot


class MemoryStore:
    """Load and save SI-1 persistent memory files safely within shared RAM limits."""

    def __init__(
        self,
        memory_dir: Path = MEMORY_DIR,
        runtime_file: Path = RUNTIME_FILE,
        facts_file: Path = FACTS_FILE,
        archive_file: Path = ARCHIVE_FILE,
        logger: Logger | None = None,
    ):
        self.memory_dir = Path(memory_dir)
        self.runtime_file = Path(runtime_file)
        self.facts_file = Path(facts_file)
        self.archive_file = Path(archive_file)
        self.logger = logger

    def load(self) -> MemorySnapshot:
        # Load blocks dynamically, accepting either root dictionaries or root arrays safely
        runtime_data = self._load_json(self.runtime_file, {})
        facts_data = self._load_json(self.facts_file, [])
        archive_data = self._load_json(self.archive_file, [])
        return MemorySnapshot.from_raw(runtime_data, facts_data, archive_data)

    def save(self, snapshot: MemorySnapshot) -> bool:
        try:
            self.memory_dir.mkdir(parents=True, exist_ok=True)
            
            # Runtime state remains pretty-printed for easy manual architect review
            self._save_json(self.runtime_file, snapshot.to_runtime_json(), compact=False)
            
            # Facts and Archive files are saved compactly to eliminate disk lag on shared memory hardware
            self._save_json(self.facts_file, snapshot.to_facts_json(), compact=True)
            self._save_json(self.archive_file, snapshot.to_archive_json(), compact=True)
            return True
        except OSError as exc:
            self._log_failure("Failed to save memory", {"error": str(exc)})
            return False

    def _load_json(self, path: Path, default: Any) -> Any:
        """FIXED: Accepts both dict and list root shapes to eliminate structural loading crashes."""
        try:
            if not path.exists():
                return deepcopy(default)
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            # Safe as long as it parses into standard JSON structures (dict or list)
            return data if isinstance(data, (dict, list)) else deepcopy(default)
        except json.JSONDecodeError as exc:
            self._log_failure("Invalid memory JSON", {"path": str(path), "error": str(exc)})
            return deepcopy(default)
        except OSError as exc:
            self._log_failure("Failed to read memory JSON", {"path": str(path), "error": str(exc)})
            return deepcopy(default)

    def _save_json(self, path: Path, data: Any, compact: bool = True) -> None:
        """Saves JSON files with optional structural compression to preserve hardware bandwidth."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            if compact:
                # Removes indentation and whitespaces, dropping disk write sizes by up to 60%
                json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
            else:
                json.dump(data, f, indent=2, ensure_ascii=False)

    def _log_failure(self, message: str, context: dict[str, Any]) -> None:
        if self.logger:
            self.logger.log_failure(message, context)
