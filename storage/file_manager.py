"""Guarded filesystem operations for SI-1."""

from __future__ import annotations

import ntpath
import os
import shutil
from datetime import datetime, timezone

from .audit_logger import AuditLogger, sha256_file, sha256_text
from .permissions import Permission
from .perimeter import Perimeter, PerimeterConfig


def file_size(path: str) -> int | None:
    if not path or not os.path.exists(path):
        return None
    if os.path.isfile(path):
        return os.path.getsize(path)
    return None


class FileManager:
    """Filesystem facade that resolves paths through the storage perimeter."""

    def __init__(
        self,
        perimeter: Perimeter | None = None,
        audit: AuditLogger | None = None,
        caller: str = "si1.runtime",
    ):
        self.perimeter = perimeter or Perimeter()
        self.audit = audit or AuditLogger()
        self.caller = caller

    @classmethod
    def with_permissions(
        cls,
        permissions: set[Permission] | None = None,
        *,
        real_root: str | None = None,
        real_working_dir: str | None = None,
        caller: str = "si1.runtime",
    ) -> "FileManager":
        config = PerimeterConfig()
        if permissions is not None:
            config.permissions = permissions
        if real_root is not None:
            config.real_root = real_root
        if real_working_dir is not None:
            config.real_working_dir = real_working_dir
        return cls(perimeter=Perimeter(config), caller=caller)

    def read_file(self, path: str, *, prompt: str | None = None, prompt_id: int | None = None) -> str:
        resolved = self._resolve_or_audit(path, Permission.READ, "read_file", prompt, prompt_id)
        before_hash = sha256_file(resolved.real_path)
        before_size = file_size(resolved.real_path)

        try:
            with open(resolved.real_path, "r", encoding="utf-8") as f:
                content = f.read()
            self._audit_success(
                prompt_id,
                prompt,
                "read_file",
                Permission.READ,
                resolved,
                before_hash,
                before_hash,
                before_size,
                before_size,
            )
            return content
        except Exception as exc:
            self._audit_failure(prompt_id, prompt, "read_file", Permission.READ, resolved, exc)
            raise

    def write_file(
        self,
        path: str,
        content: str,
        *,
        prompt: str | None = None,
        prompt_id: int | None = None,
    ) -> bool:
        resolved = self._resolve_or_audit(path, Permission.WRITE, "write_file", prompt, prompt_id)
        before_hash = sha256_file(resolved.real_path)
        before_size = file_size(resolved.real_path)

        try:
            parent = os.path.dirname(resolved.real_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(resolved.real_path, "w", encoding="utf-8") as f:
                f.write(content)
            self._audit_success(
                prompt_id,
                prompt,
                "write_file",
                Permission.WRITE,
                resolved,
                before_hash,
                sha256_file(resolved.real_path),
                before_size,
                file_size(resolved.real_path),
            )
            return True
        except Exception as exc:
            self._audit_failure(prompt_id, prompt, "write_file", Permission.WRITE, resolved, exc)
            raise

    def append_file(
        self,
        path: str,
        content: str,
        *,
        prompt: str | None = None,
        prompt_id: int | None = None,
    ) -> bool:
        resolved = self._resolve_or_audit(path, Permission.APPEND, "append_file", prompt, prompt_id)
        before_hash = sha256_file(resolved.real_path)
        before_size = file_size(resolved.real_path)

        try:
            parent = os.path.dirname(resolved.real_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(resolved.real_path, "a", encoding="utf-8") as f:
                f.write(content)
            self._audit_success(
                prompt_id,
                prompt,
                "append_file",
                Permission.APPEND,
                resolved,
                before_hash,
                sha256_file(resolved.real_path),
                before_size,
                file_size(resolved.real_path),
            )
            return True
        except Exception as exc:
            self._audit_failure(prompt_id, prompt, "append_file", Permission.APPEND, resolved, exc)
            raise

    def list_directory(self, path: str, *, prompt: str | None = None, prompt_id: int | None = None) -> list[dict]:
        resolved = self._resolve_or_audit(path, Permission.LIST, "list_directory", prompt, prompt_id)

        try:
            entries = []
            for name in sorted(os.listdir(resolved.real_path)):
                real_child = os.path.join(resolved.real_path, name)
                entries.append({
                    "name": name,
                    "type": "directory" if os.path.isdir(real_child) else "file",
                    "bytes": file_size(real_child),
                })
            self._audit_success(prompt_id, prompt, "list_directory", Permission.LIST, resolved, None, None, None, None)
            return entries
        except Exception as exc:
            self._audit_failure(prompt_id, prompt, "list_directory", Permission.LIST, resolved, exc)
            raise

    def make_directory(self, path: str, *, prompt: str | None = None, prompt_id: int | None = None) -> bool:
        resolved = self._resolve_or_audit(path, Permission.MKDIR, "make_directory", prompt, prompt_id)

        try:
            os.makedirs(resolved.real_path, exist_ok=True)
            self._audit_success(prompt_id, prompt, "make_directory", Permission.MKDIR, resolved, None, None, None, None)
            return True
        except Exception as exc:
            self._audit_failure(prompt_id, prompt, "make_directory", Permission.MKDIR, resolved, exc)
            raise

    def exists(self, path: str, *, prompt: str | None = None, prompt_id: int | None = None) -> bool:
        resolved = self._resolve_or_audit(path, Permission.READ, "exists", prompt, prompt_id)

        try:
            result = os.path.exists(resolved.real_path)
            self._audit_success(prompt_id, prompt, "exists", Permission.READ, resolved, None, None, None, None)
            return result
        except Exception as exc:
            self._audit_failure(prompt_id, prompt, "exists", Permission.READ, resolved, exc)
            raise

    def delete_file(self, path: str, *, prompt: str | None = None, prompt_id: int | None = None) -> dict[str, str]:
        resolved = self._resolve_or_audit(path, Permission.DELETE, "delete_file", prompt, prompt_id)
        before_hash = sha256_file(resolved.real_path)
        before_size = file_size(resolved.real_path)

        try:
            if not os.path.isfile(resolved.real_path):
                raise IsADirectoryError(f"delete_file only accepts files: {resolved.virtual_path}")

            trash_path = self._trash_path(resolved.real_path)
            os.makedirs(os.path.dirname(trash_path), exist_ok=True)
            shutil.move(resolved.real_path, trash_path)
            self._audit_success(prompt_id, prompt, "delete_file", Permission.DELETE, resolved, before_hash, None, before_size, None)
            return {"quarantined_to": trash_path}
        except Exception as exc:
            self._audit_failure(prompt_id, prompt, "delete_file", Permission.DELETE, resolved, exc)
            raise

    def rename(
        self,
        source: str,
        destination: str,
        *,
        prompt: str | None = None,
        prompt_id: int | None = None,
    ) -> str:
        source_resolved = self._resolve_or_audit(source, Permission.RENAME, "rename", prompt, prompt_id)
        destination_resolved = self._resolve_or_audit(destination, Permission.RENAME, "rename", prompt, prompt_id)
        before_hash = sha256_file(source_resolved.real_path)
        before_size = file_size(source_resolved.real_path)

        try:
            parent = os.path.dirname(destination_resolved.real_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            os.replace(source_resolved.real_path, destination_resolved.real_path)
            self._audit_success(
                prompt_id,
                prompt,
                "rename",
                Permission.RENAME,
                source_resolved,
                before_hash,
                sha256_file(destination_resolved.real_path),
                before_size,
                file_size(destination_resolved.real_path),
            )
            return destination_resolved.virtual_path
        except Exception as exc:
            self._audit_failure(prompt_id, prompt, "rename", Permission.RENAME, source_resolved, exc)
            raise

    def copy(
        self,
        source: str,
        destination: str,
        *,
        prompt: str | None = None,
        prompt_id: int | None = None,
    ) -> str:
        source_resolved = self._resolve_or_audit(source, Permission.COPY, "copy", prompt, prompt_id)
        destination_resolved = self._resolve_or_audit(destination, Permission.COPY, "copy", prompt, prompt_id)
        before_hash = sha256_file(destination_resolved.real_path)
        before_size = file_size(destination_resolved.real_path)

        try:
            parent = os.path.dirname(destination_resolved.real_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            shutil.copy2(source_resolved.real_path, destination_resolved.real_path)
            self._audit_success(
                prompt_id,
                prompt,
                "copy",
                Permission.COPY,
                destination_resolved,
                before_hash,
                sha256_file(destination_resolved.real_path),
                before_size,
                file_size(destination_resolved.real_path),
            )
            return destination_resolved.virtual_path
        except Exception as exc:
            self._audit_failure(prompt_id, prompt, "copy", Permission.COPY, destination_resolved, exc)
            raise

    def _trash_path(self, real_path: str) -> str:
        trash_dir = os.environ.get(
            "SI1_TRASH_DIR",
            ntpath.join(self.perimeter.config.real_working_dir, "runtime", "trash"),
        )
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        name = ntpath.basename(real_path)
        return ntpath.join(trash_dir, f"{stamp}_{name}")

    def _resolve_or_audit(
        self,
        path: str,
        permission: Permission,
        operation: str,
        prompt: str | None,
        prompt_id: int | None,
    ):
        try:
            return self.perimeter.resolve_for_operation(path, permission)
        except Exception as exc:
            self.audit.log(
                prompt_id=self._prompt_id(prompt_id),
                prompt_hash=self._prompt_hash(prompt),
                caller=self.caller,
                operation=operation,
                permission=permission.value,
                virtual_path=path,
                real_path=None,
                sha256_before=None,
                sha256_after=None,
                bytes_before=None,
                bytes_after=None,
                allowed=False,
                result="denied",
                error=str(exc),
            )
            raise

    def _prompt_id(self, prompt_id: int | None) -> int:
        return prompt_id if prompt_id is not None else self.audit.next_prompt_id()

    def _prompt_hash(self, prompt: str | None) -> str | None:
        return sha256_text(prompt) if prompt is not None else None

    def _audit_success(
        self,
        prompt_id: int | None,
        prompt: str | None,
        operation: str,
        permission: Permission,
        resolved,
        sha256_before: str | None,
        sha256_after: str | None,
        bytes_before: int | None,
        bytes_after: int | None,
    ) -> None:
        self.audit.log(
            prompt_id=self._prompt_id(prompt_id),
            prompt_hash=self._prompt_hash(prompt),
            caller=self.caller,
            operation=operation,
            permission=permission.value,
            virtual_path=resolved.virtual_path,
            real_path=resolved.real_path,
            sha256_before=sha256_before,
            sha256_after=sha256_after,
            bytes_before=bytes_before,
            bytes_after=bytes_after,
            allowed=True,
            result="success",
        )

    def _audit_failure(
        self,
        prompt_id: int | None,
        prompt: str | None,
        operation: str,
        permission: Permission,
        resolved,
        error: Exception,
    ) -> None:
        self.audit.log(
            prompt_id=self._prompt_id(prompt_id),
            prompt_hash=self._prompt_hash(prompt),
            caller=self.caller,
            operation=operation,
            permission=permission.value,
            virtual_path=getattr(resolved, "virtual_path", None),
            real_path=getattr(resolved, "real_path", None),
            sha256_before=None,
            sha256_after=None,
            bytes_before=None,
            bytes_after=None,
            allowed=False,
            result="error",
            error=str(error),
        )

