"""Structured JSONL execution logging for SI-1 with ChatML array support."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from config import RUN_LOG_FILE
from models import utc_timestamp


@dataclass
class RunLogEvent:
    """One structured execution log entry, accommodating both flat text strings or ChatML arrays."""

    timestamp: str
    user_input: str
    # FIXED: Type hint expanded to cleanly support both legacy completions or new ChatML structured array lists
    generated_prompt: str | list[dict[str, str]] 
    model_output: str
    runtime_before: dict[str, Any]
    runtime_after: dict[str, Any]
    facts_before: list[dict[str, Any]]
    facts_after: list[dict[str, Any]]
    new_facts: list[dict[str, Any]]
    memory_delta: dict[str, Any]
    execution_time_ms: dict[str, float]
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    anomalies: list[str] = field(default_factory=list)


class Logger:
    """Append-only JSONL logger that avoids crashing the runtime under hardware constraints."""

    def __init__(self, log_path: Path = RUN_LOG_FILE):
        self.log_path = Path(log_path)

    def log(self, event: RunLogEvent) -> None:
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as f:
                # asdict safely unpacks the entire tree structure, keeping line logging clean
                f.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
        except OSError as exc:
            print(f"[SI-1 logging warning] Failed to write run log: {exc}")

    def log_failure(self, message: str, context: dict[str, Any] | None = None) -> None:
        event = {
            "timestamp": utc_timestamp(),
            "level": "error",
            "message": message,
            "context": context or {},
        }
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except OSError:
            print(f"[SI-1 logging error] {message}")
