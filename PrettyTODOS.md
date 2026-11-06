# SI-1 Work Status

Status checked against `todos.md`, `CHANGELOG.md`, and current code on 2026-10-30.

## Done

- **Todo #6, confidence display:** prompt says `0.8`, matching configured default. Fact provenance remains open.
- **Todo #7, bounded history:** runtime caps retained conversation history at 10 turns.
- **Todo #1, Architect visibility:** chaos/refine thinking and drafts, Obi critique/opinion, revision, raw gate response, and runtime evidence are displayed in labeled boxes. The gate is explicitly post-hoc and cannot retract shown content. Regression coverage added.
- **Todo #5, gate injection framing:** critique and revision are JSON-encoded as untrusted data; the gate prompt says not to follow embedded directives or fake verdicts. This reduces structural confusion, but model-based semantic injection remains possible.
- **Aligned payload parsing:** parser now accepts `[ALIGNED]:` on its own line followed by the payload line, matching the documented protocol.

## In Progress

- **Todo #2, corrupt memory recovery:** timestamped copies and visible warnings exist, but startup may still use defaults and overwrite the source; quarantine/read-only decisions and behavior tests remain.
- **Todo #3, engagement verification:** deterministic heuristics are stricter but are not semantic proof; add the planned unrelated-word, short/empty critique, paraphrase, and disagreement tests.
- **Todo #4, override semantics:** current behavior is acknowledgment-only on a rejected override-bearing turn, but history/fact/archive side effects remain and lack contract tests.
- **Todo #8, tests and docs:** P3 regressions and docs were added; callback/timeout, memory-recovery, override-side-effect, and broader adversarial coverage remain.
- **P4, SQLite dual-log:** SQL classes and runtime adapters exist. They currently append twice to JSONL through the wrapper path, SQL errors propagate after the JSONL write, and adapter-level consistency/failure tests are needed. SQLite files are intended as `logs/runlog.db` and `logs/duellog.db`.

## Pending

- **Todo #6, provenance:** retain source speaker/turn, extraction method, and evidence; distinguish user claims from model inferences.
- **Todo #9, application encryption:** choose protected files and a vetted authenticated-encryption/key-management and recovery design before enabling encryption.
- **P4 verification:** install `aiosqlite` in the intended environment and rerun the full suite. SQLite is a local queryable mirror, not the planned PostgreSQL ledger.