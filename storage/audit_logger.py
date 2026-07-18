"""Audit logging for guarded storage operations."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from config import STORAGE_HASH_CHUNK_BYTES


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: str) -> str | None:
    if not path or not os.path.isfile(path):
        return None

    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(STORAGE_HASH_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class AuditEvent:
    timestamp: str
    prompt_id: int
    session_id: str
    prompt_hash: str | None
    caller: str
    operation: str
    permission: str
    virtual_path: str | None
    real_path: str | None
    sha256_before: str | None
    sha256_after: str | None
    bytes_before: int | None
    bytes_after: int | None
    allowed: bool
    result: str
    error: str | None = None


class AuditLogger:
    """Append-only audit log for storage operations."""

    def __init__(self, log_path: str | None = None, session_id: str | None = None):
        self.log_path = log_path or os.environ.get(
            "SI1_AUDIT_LOG", os.path.join("storage", "storage.log")
        )
        self.session_id = session_id or "prompt-session"
        self.prompt_id = 0

    def next_prompt_id(self) -> int:
        self.prompt_id += 1
        return self.prompt_id

    def log(
        self,
        *,
        prompt_id: int,
        caller: str,
        operation: str,
        permission: str,
        virtual_path: str | None,
        real_path: str | None,
        sha256_before: str | None,
        sha256_after: str | None,
        bytes_before: int | None,
        bytes_after: int | None,
        allowed: bool,
        result: str,
        prompt_hash: str | None = None,
        error: str | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            timestamp=utc_now_iso(),
            prompt_id=prompt_id,
            session_id=self.session_id,
            prompt_hash=prompt_hash,
            caller=caller,
            operation=operation,
            permission=permission,
            virtual_path=virtual_path,
            real_path=real_path,
            sha256_before=sha256_before,
            sha256_after=sha256_after,
            bytes_before=bytes_before,
            bytes_after=bytes_after,
            allowed=allowed,
            result=result,
            error=error,
        )
        self._append(event)
        return event

    def _append(self, event: AuditEvent) -> None:
        log_dir = os.path.dirname(self.log_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
