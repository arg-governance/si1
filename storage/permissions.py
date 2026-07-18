"""Storage permission enum."""

from __future__ import annotations

from enum import Enum


class Permission(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    APPEND = "APPEND"
    MKDIR = "MKDIR"
    DELETE = "DELETE"
    LIST = "LIST"
    RENAME = "RENAME"
    COPY = "COPY"

