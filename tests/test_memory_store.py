from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


class TestAtomicMemoryPersistence(unittest.TestCase):
    def test_save_replaces_json_and_leaves_no_temp_file(self) -> None:
        from memory_store import MemoryStore
        from models import ArchiveEntry, RuntimeState

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime_path = root / "memory" / "runtime.json"
            facts_path = root / "memory" / "facts.json"
            archive_path = root / "memory" / "archive.json"
            runtime_path.parent.mkdir(parents=True)
            runtime_path.write_text('{"old":true}', encoding="utf-8")
            store = MemoryStore(runtime_path, facts_path, archive_path)

            asyncio.run(store.save(RuntimeState(turn=7), [], [ArchiveEntry("t", "s")]))

            self.assertEqual(json.loads(runtime_path.read_text(encoding="utf-8"))["turn"], 7)
            self.assertEqual(json.loads(facts_path.read_text(encoding="utf-8")), [])
            self.assertEqual(len(json.loads(archive_path.read_text(encoding="utf-8"))), 1)
            self.assertEqual(list(runtime_path.parent.glob(".*.tmp")), [])

    def test_atomic_replace_failure_preserves_old_file_and_is_reported(self) -> None:
        from memory_store import MemoryStore
        from models import ArchiveEntry, RuntimeState

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runtime.json"
            path.write_text('{"old":true}', encoding="utf-8")

            with patch("memory_store.os.replace", side_effect=OSError("simulated replace failure")):
                with self.assertRaisesRegex(OSError, "simulated replace failure"):
                    asyncio.run(MemoryStore._save_json(path, {"new": True}))

            self.assertEqual(path.read_text(encoding="utf-8"), '{"old":true}')
            self.assertEqual(list(path.parent.glob(".*.tmp")), [])

            invalid_destination = path.parent / "runtime-directory"
            invalid_destination.mkdir()
            store = MemoryStore(
                runtime_file=invalid_destination,
                facts_file=path.parent / "facts.json",
                archive_file=path.parent / "archive.json",
            )
            with self.assertRaisesRegex(OSError, "runtime-directory"):
                asyncio.run(store.save(RuntimeState(), [], [ArchiveEntry("t", "s")]))


if __name__ == "__main__":
    unittest.main()
