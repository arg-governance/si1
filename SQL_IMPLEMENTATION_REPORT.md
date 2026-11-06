# SQL Implementation Report

## Summary

The runtime uses SQLite as its relational query layer, implemented through Python's async SQLite driver `aiosqlite`.

This is not a separate database service. It is a local embedded SQLite database stored next to the JSONL logs, used as a queryable mirror of the same audit data rather than as the sole source of truth.

## Database choice

- Database engine: SQLite
- Python driver: `aiosqlite`
- Reason: embedded, local-first, zero external server, suitable for a single-machine SI-1 runtime with audit log queries

## What is implemented

- `sql_logger.py` defines `SQLLogger` for execution log mirroring.
- `sql_logger.py` defines `SQLDuelLog` for duel/audit log mirroring.
- Both classes write rows into SQLite tables; the dual adapters in `si1.py` send runtime events to the existing JSONL logger and the SQL logger.
- **Single-append ownership:** Fixed. The primary `Logger`/`DuelLog` owns the JSONL append; `SQLLogger`/`SQLDuelLog` are SQLite-only sinks. The runtime dual adapters call each sink once.
- Database files are created adjacent to the log files, such as `logs/runlog.db` and `logs/duellog.db`.

## Data model and behavior

- JSONL remains the primary auditor-facing record stream.
- SQL is an indexed, queryable secondary store.
- Redaction is still applied to runtime execution events before they are written to either destination.
- The SQL log tables include indexes on timestamp, event, turn, round, actor, and kind to support common queries.

## Files involved

- `sql_logger.py`
- `si1.py`
- `requirements.txt`
- `logs/runlog.jsonl` / `logs/runlog.db`
- `logs/duellog.json` / `logs/duellog.db`

## Verification status (2026-11-06)

- The three focused P3 regressions pass after installing `aiosqlite` in the configured system Python environment.
- The full test suite passes in the configured Windows venv: `Ran 47 tests — OK`.
- Regression coverage invokes both runtime dual adapters and asserts one JSONL record plus one SQL row per event. It also checks direct SQL-only logging does not create JSONL.
- SQL errors still propagate after the primary JSONL write; failure policy and degraded-mode behavior need a separate decision and tests.

## Current status

SQL logger classes and runtime dual-write wiring are present, but P4 is **in progress**, not complete. Intended local SQLite files are `logs/runlog.db` and `logs/duellog.db`; they are queryable mirrors, not PostgreSQL and not encrypted.

It is intentionally separate from encryption. The SQL layer provides queryable audit storage, not application-level encryption at rest.
