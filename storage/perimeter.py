"""Virtual filesystem perimeter for SI-1 storage access."""

from __future__ import annotations

import ntpath
import os
from dataclasses import dataclass, field
from pathlib import PureWindowsPath

from .permissions import Permission


class PerimeterError(Exception):
    """Base storage perimeter error."""


class PermissionDenied(PerimeterError):
    """Raised when an operation lacks required permission."""


class PathViolation(PerimeterError):
    """Raised when a path violates the virtual perimeter."""


@dataclass(frozen=True)
class ResolvedPath:
    virtual_path: str
    real_path: str


@dataclass
class PerimeterConfig:
    virtual_root: str = r"C:\\"
    virtual_working_dir: str = r"C:\\SI-1"
    real_root: str = field(default_factory=lambda: os.environ.get("SI1_REAL_ROOT", r"D:\\"))
    real_working_dir: str = field(
        default_factory=lambda: os.environ.get("SI1_REAL_WORKING_DIR", r"D:\\SI-1")
    )
    permissions: set[Permission] = field(default_factory=lambda: set(Permission))
    blocked_filenames: set[str] = field(
        default_factory=lambda: {"si1.py", "python.exe", "pythonw.exe"}
    )


class Perimeter:
    """Resolve and validate virtual paths before storage access."""

    def __init__(self, config: PerimeterConfig | None = None):
        self.config = config or PerimeterConfig()

    def require(self, permission: Permission) -> None:
        if permission not in self.config.permissions:
            raise PermissionDenied(f"Permission denied: {permission.value}")

    def resolve(self, path: str) -> ResolvedPath:
        virtual_path = self._normalize_virtual(path)
        real_path = self._virtual_to_real(virtual_path)
        self._assert_inside_real_root(real_path)
        self._assert_not_blocked(real_path)
        return ResolvedPath(virtual_path=virtual_path, real_path=real_path)

    def resolve_for_operation(self, path: str, permission: Permission) -> ResolvedPath:
        self.require(permission)
        return self.resolve(path)

    def _normalize_virtual(self, path: str) -> str:
        if not path or not path.strip():
            raise PathViolation("Path is empty")

        candidate = path.strip().replace("/", "\\")
        parsed = PureWindowsPath(candidate)

        if not parsed.is_absolute():
            candidate = ntpath.join(self.config.virtual_working_dir, candidate)

        normalized = ntpath.normpath(candidate)
        drive, tail = ntpath.splitdrive(normalized)

        if drive and drive.upper() != "C:":
            raise PathViolation(f"Only the virtual C: drive is available: {drive}")

        if not drive:
            normalized = ntpath.join("C:\\", tail.lstrip("\\"))

        return normalized

    def _virtual_to_real(self, virtual_path: str) -> str:
        drive, tail = ntpath.splitdrive(virtual_path)
        if drive.upper() != "C:":
            raise PathViolation(f"Unexpected virtual drive: {drive}")

        relative = tail.lstrip("\\")
        real_path = ntpath.join(self.config.real_root, relative)
        return ntpath.normpath(real_path)

    def _assert_inside_real_root(self, real_path: str) -> None:
        root = ntpath.normcase(ntpath.abspath(self.config.real_root))
        target = ntpath.normcase(ntpath.abspath(real_path))

        if target != root and not target.startswith(root.rstrip("\\") + "\\"):
            raise PathViolation(f"Path escapes real root: {real_path}")

    def _assert_not_blocked(self, real_path: str) -> None:
        filename = ntpath.basename(real_path).lower()
        if filename in {name.lower() for name in self.config.blocked_filenames}:
            raise PathViolation(f"Direct access blocked: {filename}")

