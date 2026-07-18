"""Persistent data models, delta analysis mechanisms, and structure mapping for SI-1."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


def utc_timestamp() -> str:
    """Return an ISO-8601 timestamp for runtime records."""
    return datetime.now().isoformat()


@dataclass
class RuntimeState:
    """Mutable runtime state persisted between SI-1 turns."""

    last_input: str = ""
    last_output: str = ""
    session_count: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "RuntimeState":
        if not isinstance(data, dict):
            return cls()
        return cls(
            last_input=str(data.get("last_input", "")),
            last_output=str(data.get("last_output", "")),
            session_count=int(data.get("session_count", 0) or 0),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Fact:
    """A structured fact entry stored in memory with unified architectural alignment."""

    id: int
    statement: str  # FIXED: Renamed text to statement to match PromptEngine and Validator definitions
    confidence: float = 0.8
    created: str = field(default_factory=utc_timestamp)
    updated: str = field(default_factory=utc_timestamp)
    status: str = "active"
    type: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Fact":
        # FIXED: Handles input from data sources whether they used the legacy key 'text' or new 'statement'
        raw_statement = data.get("statement", data.get("text", ""))
        return cls(
            id=int(data.get("id", 0) or 0),
            statement=str(raw_statement),
            confidence=float(data.get("confidence", 0.8) or 0.8),
            created=str(data.get("created", utc_timestamp())),
            updated=str(data.get("updated", utc_timestamp())),
            status=str(data.get("status", "active")),
            type=data.get("type"),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if data["type"] is None:
            data.pop("type")
        return data


@dataclass
class ArchiveEntry:
    """A compact persisted summary of one interaction."""

    time: str
    summary: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ArchiveEntry":
        return cls(
            time=str(data.get("time", utc_timestamp())),
            summary=str(data.get("summary", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MemorySnapshot:
    """Complete persisted memory loaded by the runtime with multi-type shape safety."""

    runtime: RuntimeState = field(default_factory=RuntimeState)
    facts: list[Fact] = field(default_factory=list)
    archive: list[ArchiveEntry] = field(default_factory=list)

    def to_runtime_json(self) -> dict[str, Any]:
        return self.runtime.to_dict()

    def to_facts_json(self) -> list[dict[str, Any]]:
        # FIXED: Outputs a clean, lightweight list array matching memory_store compact requirements
        return [fact.to_dict() for fact in self.facts]

    def to_archive_json(self) -> list[dict[str, Any]]:
        # FIXED: Outputs a clean, lightweight list array matching memory_store compact requirements
        return [entry.to_dict() for entry in self.archive]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the full snapshot (runtime + facts + archive) to a single dict."""
        return {
            "runtime": self.runtime.to_dict(),
            "facts": self.to_facts_json(),
            "archive": self.to_archive_json(),
        }

    def facts_to_list(self) -> list[dict[str, Any]]:
        """Alias for to_facts_json() used by the run-log emitter."""
        return self.to_facts_json()

    def clone(self) -> "MemorySnapshot":
        return MemorySnapshot.from_raw(
            self.to_runtime_json(),
            self.to_facts_json(),
            self.to_archive_json(),
        )

    @classmethod
    def from_raw(
        cls,
        runtime_data: dict[str, Any] | None,
        facts_data: Any,
        archive_data: Any,
    ) -> "MemorySnapshot":
        """FIXED: Intelligently accepts database data arrays regardless of nested dictionary wrappers."""
        
        # 1. Parse Facts safely out of nested objects OR flat lists
        if isinstance(facts_data, dict):
            facts_raw = facts_data.get("facts", [])
        elif isinstance(facts_data, list):
            facts_raw = facts_data
        else:
            facts_raw = []

        # 2. Parse Archives safely out of nested objects OR flat lists
        if isinstance(archive_data, dict):
            archive_raw = archive_data.get("sessions", [])
        elif isinstance(archive_data, list):
            archive_raw = archive_data
        else:
            archive_raw = []

        return cls(
            runtime=RuntimeState.from_dict(runtime_data),
            facts=[Fact.from_dict(item) for item in facts_raw if isinstance(item, dict)],
            archive=[ArchiveEntry.from_dict(item) for item in archive_raw if isinstance(item, dict)],
        )


@dataclass
class MemoryDelta:
    """Structured report of changes between two memory snapshots."""

    added_facts: list[Fact] = field(default_factory=list)
    removed_facts: list[Fact] = field(default_factory=list)
    modified_facts: list[dict[str, Any]] = field(default_factory=list)
    runtime_changes: dict[str, dict[str, Any]] = field(default_factory=dict)
    archive_changes: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def compare(cls, before: MemorySnapshot, after: MemorySnapshot) -> "MemoryDelta":
        before_facts = {fact.id: fact for fact in before.facts}
        after_facts = {fact.id: fact for fact in after.facts}

        added = [fact for fact_id, fact in after_facts.items() if fact_id not in before_facts]
        removed = [fact for fact_id, fact in before_facts.items() if fact_id not in after_facts]
        modified = []
        for fact_id, after_fact in after_facts.items():
            before_fact = before_facts.get(fact_id)
            if before_fact and before_fact.to_dict() != after_fact.to_dict():
                modified.append({
                    "id": fact_id,
                    "before": before_fact.to_dict(),
                    "after": after_fact.to_dict(),
                })

        runtime_changes = {}
        before_runtime = before.runtime.to_dict()
        after_runtime = after.runtime.to_dict()
        for key, before_value in before_runtime.items():
            after_value = after_runtime.get(key)
            if before_value != after_value:
                runtime_changes[key] = {"before": before_value, "after": after_value}

        archive_changes: dict[str, Any] = {}
        if len(before.archive) != len(after.archive):
            archive_changes["count"] = {
                "before": len(before.archive),
                "after": len(after.archive),
            }
        if before.archive != after.archive:
            archive_changes["latest"] = after.archive[-1].to_dict() if after.archive else None

        return cls(
            added_facts=added,
            removed_facts=removed,
            modified_facts=modified,
            runtime_changes=runtime_changes,
            archive_changes=archive_changes,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "added_facts": [fact.to_dict() for fact in self.added_facts],
            "removed_facts": [fact.to_dict() for fact in self.removed_facts],
            "modified_facts": self.modified_facts,
            "runtime_changes": self.runtime_changes,
            "archive_changes": self.archive_changes,
        }
