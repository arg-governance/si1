# SI-1 Changelog

## [Unreleased] — Fix duplicate JSONL dual-log writes

### Fixed
- `SQLLogger` and `SQLDuelLog` now write only to SQLite. The primary `Logger` and `DuelLog` own JSONL appends, so the `SI1Runtime` dual adapters produce exactly one JSONL record and one SQL row per event.
- SQL database initialization creates its parent directory when needed.
- Dual logger type contracts now use structural protocols, matching the JSONL and SQLite sink implementations.

### Tests
- Added a regression covering one JSONL line and one SQL row for both run and duel events, plus a direct SQL-only call that must not create JSONL.
- Full suite: `python -m unittest discover -s tests -p "test_*.py" -q` → 47 passed.

---

## [Unreleased] — Rails chat boot and Python service bridge

### Fixed
- Restored the Rails environment, development/test/production configuration, SQLite database config, and base controller required by `config.ru` and the HTML chat view.
- Changed `ChatController` to proxy JSON to the Python backend (`SI1_PYTHON_BACKEND_URL`) instead of requiring `.py` modules as Ruby or calling a nonexistent `run_turn` method.
- Replaced the Flask adapter's removed `before_first_request` hook, undefined `_runtime_obj`, and un-awaited memory load with lazy runtime initialization and one-turn async execution. Added `/health` and per-request phase-trace capture for the Rails UI.
- Changed chat rendering to use DOM text nodes so user and model content is not interpreted as HTML.

### Verification
- Added `tests/test_rubyonrials_backend.py` for health, request validation, prompt forwarding, phase trace output, and request-state restoration.
- `python -m unittest discover -s tests -p "test_*.py" -q` passes in the configured Python environment.
- Rails boot was not executable in this workspace because Ruby and Bundler are not installed; see `rubyonrials/README.md` for launch steps.

---

## [Unreleased] — Architect transparency and gate input hardening

### Changed
- **Architect mode now exposes every duel phase.** Chaos thought/draft, Obi critique/opinion, Lucifer refine thought/revision, raw gate response, and runtime per-hook evidence are shown in labeled boxes as each phase completes. Progress markers remain visible while generation is running. Obi's verdict is a post-hoc audit and cannot retract already displayed content; this mode is for the private Architect workflow, not a public safety boundary.
- **Gate input is framed as untrusted JSON data.** Obi is instructed not to follow embedded requests, role changes, policy claims, or fake verdict text. This reduces structural confusion but does not prevent semantic prompt injection; Obi's judgment remains model-dependent.
- **Aligned payload parsing now matches the prompt contract.** `find_aligned_payload` accepts `[ALIGNED]:` on its own line followed by the four-bit payload line.
- **Documentation reflects implementation boundaries.** README, architecture, and constitutional prompts describe Architect transparency, actual gate sampling, and residual model-dependent risk rather than claiming a deterministic semantic gate.

### Tests
- Added regressions for hostile JSON gate framing, boxed visibility of all phase content on ACCEPT/REJECT, and the token-on-own-line payload format.
- Focused P3 tests: 3 passed. Full suite: `python -m unittest discover -s tests -p "test_*.py" -q` → 44 passed.

---

## [Unreleased] — SQLite dual-log audit storage

### Added
- **SQLite dual-log backend.** The runtime now keeps the JSONL audit files and writes the same entries to SQLite databases via `aiosqlite`, providing queryable event storage without replacing the existing JSONL source-of-truth.
- **Dual logging wiring.** `SI1Runtime` exposes `sql_logger` and `sql_duel_log`, and the runtime writes through dual logger adapters so both the original JSONL loggers and the SQLite-backed loggers record the same events.
- **Indexed audit tables.** `sql_logger.py` creates SQLite tables for run events and duel events with indexes for timestamp, event, turn, round, kind, and actor queries.
- **Redacted runtime logging.** Execution events continue to redact sensitive prompt/output fields before writing to either JSONL or SQLite stores.

### Verification
- `python -m unittest discover -s tests -p "test_*.py" -q` → `Ran 41 tests in 0.361s — OK`

---

## [Unreleased] — Tool-call replay, single-round loop, runtime consistency

### Fixed
- **OpenAI-style tool loop is now the runtime default.** The main HTTP completion methods in `runtime_components.py` now execute tool calls emitted by the model, append the tool results to the conversation, and continue until the model returns a plain text answer or the tool loop limit is reached. This resolves the earlier silent failure where tool-enabled backends could return an empty `GenerationResult` after emitting a valid `tool_calls` payload.
- **Tool use is documented as transport-level behavior, not custom prompt syntax.** The canonical contract is `tools + tool_choice`, not a meta tag like `use tools`. Both models now use `tool_choice="auto"`; the tool schema is available without forcing a tool call on every completion. Streamed completions execute and replay tool calls as well as non-streaming completions.
- **Memory writes replace each file atomically.** `MemoryStore` writes and syncs a same-directory temporary file before replacing the destination, and reports per-file save failures. The three-file save is not a cross-file transaction, and recovery of already-corrupt files remains future work.
- **Documentation and runtime now agree on the single-round loop and sampling values.** The project has one canonical contract: four phases exactly once, chaos at temperature 0.4, and tool use enabled by request payload rather than a magic string.
- **Direct architect-tag prompts are supported.** `[LUCIFER]: ...` and `[OBI]: ...` are now recognized as one-to-one convenience prompts that bypass the full duel for that single interaction.

### Added
- **Regression coverage for the tool replay path.** `tests/test_smoke_tests.py` includes a regression asserting that `run_messages()` keeps consuming `tool_calls` until it reaches a non-tool completion.
- **Green terminal output for Lucifer tool executions.** Bash tool calls from Lucifer print the command and result in green ANSI color, making each tool use visible in the terminal.

### Verification
- `python -m unittest tests.test_smoke_tests -q` → `Ran 14 tests in 0.256s — OK`
- GitHub push is intentionally deferred until local architect testing is finished and approval is granted.

---

## [Unreleased] — Single-round loop fix, Obi opinion split, tests

### Fixed
- **Loop runaway.** The four-phase duel loop was running up to 50
  unbounded rounds because `config.MAX_DUEL_ROUNDS = 2` paired with
  `for round_idx in range(config.MAX_DUEL_ROUNDS):` re-ran all four
  phases per iteration and re-used the rejected mutation as the next
  chaos-phase input. Pinned to **1 round per loop, 4 steps total**:
  Chaos → Discipline → Refine → Gate, then the loop ends. After a
  gate REJECT the runtime surfaces a hard-reject fallback
  immediately; the Architect re-issues the prompt (optionally with
  a `[OVERRIDE]:` prefix) to retry.
  - `config.py`: `MAX_DUEL_ROUNDS = 1` (was 2). Comment block now
    describes the single-round contract.
  - `si1.py`: removed the `for round_idx in range(...)` scaffolding
    entirely. `_generate_with_observer` is now a straight-line
    pass through the four phases. A defensive
    `assert config.MAX_DUEL_ROUNDS == 1` is in place so a future
    change can't silently re-introduce the nested-round logic.
  - `core/system.md` / `docs/architecture.md`: documentation now
    says "capped at MAX_DUEL_ROUNDS (currently 1) round" instead
    of "2 rounds".
- **Dead helper.** Removed `_ensure_thought_open` from `si1.py` —
    the function body was `pass` and the comment above it referenced
    a non-existent `_open_once` closure. Thought-channel opening is
    handled inline by `_on_thought_token`.
- **Dead config.** Removed `OBI_GUARD_RULES` (with
    `disallowed_keywords` and `max_critique_rounds`) from
    `config.py`. Defined but never read anywhere — leftover from
    the JSON-validator era.
- **Stale doc.** `core/observer_system.md` "recursion budget"
    section now says "1 round" (was "2 rounds"), matching the
    runtime contract.

### Added
- **Obi's independent read of the Architect's prompt.** Obi's
  discipline-phase output now ends (optionally) with a fifth block
  headed `My view on the Architect's prompt:`. This is Obi's honest
  take on the *prompt itself* — not on Lucifer's draft — and is
  surfaced to the Architect separately. It is **not** fed to Lucifer
  during the Refined Learning Pass (Lucifer cannot revise the
  Architect's prompt; only the four hooks drive a revision).
  - `core/observer_system.md`: the discipline-phase contract is
    extended with the fifth block, hard rules for what counts as
    a real take (no hedges, no "looks fine to me"), and a note
    that the opinion is logged but does not affect the gate.
  - `models.py`: new `split_architect_opinion(text)` helper that
    cleanly separates the hooks portion from the opinion portion
    using a case-insensitive header match. Empty body returns
    `""` (not `None`) so the runtime still logs that Obi emitted
    the header with nothing to add.
  - `si1.py`: after the discipline phase, the runtime splits
    Obi's critique, streams the opinion to the Architect under the
    labelled header `[obi's view on the architect's prompt]`, logs
    it to `duellog.json` under `kind="architect_opinion"`, then
    reassigns `critique_text = hooks_text` so the refine-phase
    build_messages call only sees the hooks.
- **Test suite.** New `tests/test_loop_structure.py` (11 tests)
  pins the single-round contract:
  - `MAX_DUEL_ROUNDS == 1`
  - no `for ... in range(MAX_DUEL_ROUNDS)` anywhere in `si1.py`
  - defensive `assert MAX_DUEL_ROUNDS == 1` inside
    `_generate_with_observer`
  - `critique_stream` is called with `draft=draft`
  - the revise phase uses the DRAFT as a prior assistant turn
  - Obi is **not** called in the refine phase
  - `run_iteration` calls `_generate_with_observer` exactly once
  - exactly one chaos-phase `kind="draft"` call site
  - all four phase-done log markers present
  And new `TestArchitectOpinionSplit` (4 tests) +
  `TestArchitectOpinionWiring` (4 tests) pin the opinion-split
  wiring: helper behavior, header visibility, `architect_opinion`
  duellog kind, and that the split happens *before* the
  `critique_text` reassignment so Lucifer never sees the opinion.
- **`tests/README.md`.** Documents the two test files and the
  pinning contracts.

### Test results
- `python -m unittest discover -s tests -p "test_*.py"` →
  `Ran 25 tests in 0.130s — OK` (6 smoke + 19 loop-structure).

### Migration notes
- No public API changes. `_generate_with_observer` still returns
  the same 4-tuple `(text, accepted_round, last_reject_reason,
  already_streamed)`; `accepted_round` is now always `0` on
  success and the only legal values are `0` (accepted) or `None`
  (hard reject). Callers that compared `accepted_round > 0` are
  unreachable — every accepted mutation comes from round 0.
- Obi's discipline output gains an optional fifth block. Old
  models that don't emit it will still work: the runtime treats
  a missing header as "no opinion this turn" and continues.


## [Unreleased] — Messages API, thought channel routing, multi-turn revise

Replaces the legacy single-string 
un(prompt=...) / stream(prompt=...)
API with a real messages=[...] ChatML list so llama-server can apply
Gemma-4's chat template (`<|turn>role\\n...<turn|>`) instead of mashing
everything into one user blob. Adds a ThoughtRouter that strips Gemma-4's
`<|channel>thought` reasoning blocks from the duellog and streams them
to a separate visual channel, and threads the revise phase as a real
multi-turn conversation (chaos draft + Obi's critique as actual turns)
so the model sees its own output rather than a concatenated blob.

### Added
1. **Generate — messages support.** New 
un_messages(model_id, messages=[...])
   and stream_messages(model_id, messages=[...]) methods that pass a
   real ChatML messages list to the API. Original 
un / stream
   are kept as thin wrappers for back-compat with existing call sites.

2. **PromptEngine.build_messages() — returns structured ChatML list.**
   Signature: uild_messages(system_prompt, context_block, user_input,
   prior_turns=None) -> list[dict[str, str]]. Returns `[{"role": ..., "content": ...}, ...]`
   with system first and the latest user turn carrying both the
   kernel context and the Architect's prompt. prior_turns lets callers
   thread prior conversation as real user / ssistant turns.

3. **si1.py — proper messages for chaos + refine + revise.**
   - Chaos phase: [system, user] (system = Lucifer constitution;
     user = runtime note + kernel context + Architect prompt).
   - Refine phase: [system, user] with the kernel context wrapped
     around Obi's critique (so the model sees context + critique as
     one user turn, not a separate system message).
   - Revise phase: [system, user(chaos prompt), assistant(chaos draft),
     user(critique + revise prompt)] — multi-turn so the model sees
     its own previous output.

4. **ThoughtRouter in runtime_components.py — Gemma-4 reasoning stripper.**
   State machine that consumes streamed tokens, detects `<|channel>thought\\n`
   / `<channel|>` (Gemma-4 native) and the legacy `<think>` /
   `<reasoning>` pairs, and routes their content to on_thought while
   passing the actual answer to on_normal. The wrapper tags themselves
   are NEVER passed to either writer. The router is robust to tag
   boundaries that split across tokens (`<|cha` + `nnel>thought\\n`).

5. **Speak.thought() — visual thought channel.** New open_thought /
   write_thought / close_thought async API that writes to sys.stderr
   with ANSI dim+italic (`\\x1b[2;3m ... \\x1b[0m`) prefixed with the
   marker `"  ⌞ "` (U+231E) when stderr is a TTY. When stderr is
   captured (file / pipe), ANSI codes are skipped and a
   `[thought]...[/thought]` marker wraps the content so non-TTY logs
   still preserve the channel split.

### Tests
- 	est_smoke_tests.py — 6 smoke tests covering all 5 changes:
  - 	est_1_messages_structure: PromptEngine + Generate API surface
  - 	est_2_build_messages: build_messages returns valid ChatML list,
    with and without prior_turns
  - 	est_3_si1_uses_messages: si1.py contains chaos / refine / revise
    and calls build_messages
  - 	est_4_thought_router: ThoughtRouter detects `<|channel>thought\\n`
    / `<channel|>` and routes correctly
  - 	est_5_speak_thought: Speak has _THOUGHT_OPEN_ANSI class attr and
    emits the [thought] marker / ANSI codes
  - 	est_6_full_integration: end-to-end messages structure for chaos
    (2 msgs) and refine (5 msgs, multi-turn)

Run with:
`
cd /opt/si1
python -m unittest tests.test_smoke_tests -v
`
All 6 tests pass.

### Back-compat
- 
un / stream (single-prompt) remain functional; new code prefers
  
un_messages / stream_messages.
- ThoughtRouter is opt-in: Speak.write still works as before for
  callers that don't route a separate thought channel.


## [Unreleased]

## [2026-07-27] โ€” Architect-facing audit surface + chaos-phase protocol wrapper

Follow-up to the 2026-07-27 hardening pass. The runtime was surfacing
only the chaos-phase stream and the final response / fallback to the
Architect on stdout. Obi's discipline critique, the revise mutation,
and the gate verdict lived only in `duellog.json`. Re-reading
`core/system.md` ("the framework you operate under is the mitigation:
explicit principles, a separate observer, persistent memory, and an
Architect who audits") and `core/observer_system.md` (Obi's role,
four-hook contract, gate protocol) made it clear the runtime was
over-sharing the chaos draft and under-sharing the audit trail. This
release surfaces Obi's gate verdict on every round and enriches the
fallback message with Obi's actual reason, plus adds a runtime-side
chaos-phase prompt wrapper so Lucifer doesn't emit `[ALIGNED]:` or
`[META]` while he's still in chaos.

### Added
- `si1.py`: After every gate verdict, the runtime prints a labelled
  line via `Speak.run`: `[obi gate (round N): ACCEPTED]` on accept or
  `[obi gate (round N): REJECT โ€” <reason>]` on reject. The discipline
  critique and the revise mutation remain internal-only and live in
  `duellog.json` for the auditor (per the original protocol scope),
  but the gate verdict โ€” the audit outcome โ€” now reaches stdout so the
  Architect doesn't have to `cat duellog.json` after every turn to
  learn what Obi decided.
- `si1.py`: `_generate_with_observer` now returns a 3-tuple
  `(text, accepted_round, last_reject_reason)`. `last_reject_reason`
  is Obi's reason string from the final round's gate, or a
  per-phase network-failure description (e.g. `"gate-phase network
  failure: ClientError(...)"`), or `None` if the loop accepted on
  round 0. `run_iteration` surfaces this in the fallback message
  when `_generate_with_observer` returns `(None, None, reason)`:
  `"...Obi rejected the revised draft on the final round. Obi said:
  <reason>. ..."` The Architect now sees the actual reason on a hard
  reject, not just the existence of the reject.
- `si1.py`: Runtime-side chaos-phase prompt wrapper. `core/system.md`
  instructs Lucifer to prefix every "final text block" with
  `[ALIGNED]:` and to emit a `[META]` block for epistemic counts.
  Lucifer obeys faithfully, including in the chaos phase where
  neither artifact is appropriate โ€” the chaos draft is raw,
  unfiltered, and not yet ready for the gate. The runtime now wraps
  the chaos-phase prompt with a 7-line `[RUNTIME NOTE โ€” CHAOS PHASE]`
  preamble that explicitly tells Lucifer: "Do NOT emit the compliance
  token `[ALIGNED]:` or the 4-bit payload โ€” those are for the
  Refined Learning Pass (Phase 3) only. Do NOT emit a `[META]`
  block." The system prompt in `core/system.md` is unchanged; this
  is a runtime-side annotation, not a protocol change.

### Verified
- `python3 -m py_compile si1.py runtime_components.py models.py
  memory_store.py logger.py prompt_engine.py fact_extractor.py
  fact_validator.py config.py` โ’ 0 errors.
- Smoke test A (gate ACCEPT round 0): `_generate_with_observer`
  returns `(mutation, 0, None)`; chaos stream prints without
  `[ALIGNED]:`/`[META]` artifacts.
- Smoke test C (gate REJECT both rounds): speak buffer contains
  `[obi gate (round 0): REJECT โ€” <reason>]`, `[obi gate (round 1):
  REJECT โ€” <reason>]`, and the fallback message includes
  `"Obi said: <reason>."`. No `RuntimeWarning` even with
  `-W error::RuntimeWarning`.
- The chaos-phase prompt wrapper preserves the protocol semantics โ€”
  `core/system.md` is unchanged, and Lucifer's behaviour on the
  refine phase is unaffected (it still receives the `[ALIGNED]:`
  instruction via the existing refine-prompt template, not the
  chaos-phase wrapper).

## [2026-07-27] โ€” Chaos-phase typewriter fix + async-callback ordering

Follow-up to the 2026-07-27 hardening pass. The chaos-phase typewriter
stream was producing one visual line per token (because `Speak.run`
appended `"\n"` to every write), and the `AsyncTokenStream.on_token`
hook was emitting `RuntimeWarning: coroutine ... was never awaited`
when callers passed a coroutine function. Both fixed.

### Fixed
- `runtime_components.py`: `Speak` gained two new methods alongside the
  existing `run(text)`:
  - `write(text)` โ€” writes `text` to the underlying stream **without**
    appending a newline. The chaos-phase typewriter effect now uses
    this so all model tokens in one stream share a single visual line
    instead of one line per token.
  - `flush()` โ€” flushes the underlying stream without writing anything.
    Useful for explicit flush points inside a multi-token write
    sequence.

  `run(text)` is unchanged and remains the right choice for whole-line
  output (final responses, log lines, fallback messages). `write` and
  `run` can be freely interleaved: every call is a complete atomic-ish
  write+flush under a single `asyncio.to_thread`.
- `runtime_components.py`: `AsyncTokenStream.__anext__` now **awaits**
  async `on_token` callbacks instead of scheduling them with
  `asyncio.ensure_future`. The previous fire-and-forget dispatch
  preserved throughput but let tokens reorder when the callback did any
  I/O (e.g. `Speak.write` hops a thread). Awaiting the callback
  back-pressures the stream (the desired behaviour for typewriter-style
  output) and guarantees arrival order. Sync callbacks are still fired
  inline with no `await` cost. Both signatures are auto-detected via
  `asyncio.iscoroutine(result)`.
- `si1.py`: The chaos-phase `on_token` callback now calls
  `self.speaker.write(token)` instead of `self.speaker.run(...)`, so
  the typewriter effect produces one continuous line per chaos phase.
  A `[chaos-phase streaming Lucifer's draftโ€ฆ]` header is printed
  before the stream starts, and a `[chaos: N chars. running discipline
  โ’ refine โ’ gateโ€ฆ]` separator is printed after the stream ends, so
  the user knows the silent discipline and refine phases are still in
  flight before any final response or fallback appears.
- `runtime_components.py`: No more `RuntimeWarning: coroutine ... was
  never awaited` from `AsyncTokenStream.__anext__` when callers pass a
  coroutine function as `on_token`. Verified with `-W error::RuntimeWarning`.

### Verified
- `python3 -m py_compile si1.py runtime_components.py models.py
  memory_store.py logger.py prompt_engine.py fact_extractor.py
  fact_validator.py config.py` โ’ 0 errors.
- Smoke test: `AsyncTokenStream` with a coroutine `on_token` that
  awaits `Speak.write` produces `'Hello world! This is streamed.\n'`
  in a `StringIO` buffer (six tokens, one trailing newline, no
  `RuntimeWarning` even with `-W error::RuntimeWarning`).
- End-to-end smoke: `SI1Runtime._generate_with_observer` with a fake
  Lucifer streaming three tokens (`'Hello'`, `' world'`, `'!'`) and a
  fake Obi returning `ACCEPTED` returns `(mutation, 0)` on round 0
  with no warnings and no exceptions.
- The 2026-07-27 entry below describes the previous (incorrect) state
  โ€” it said tokens went through `Speak.run` and that the callback was
  sync-only. Both statements are corrected by this follow-up.

## [2026-07-27] โ€” Async architecture hardening (Lucifer โ Obi HTTP)

Senior-dev pass on the four-phase duel loop and the wire layer between the
runtime and the two `llama-server` processes (Lucifer on 666, Obi on 999).
No protocol-level changes; the Four-Hook Contract and Lucifer/Obi separation
are preserved as designed.

### Added
- `runtime_components.py`: `Generate.__init__` accepts a new `timeout_s`
  parameter (default 600.0). The value is the single source of truth for
  the HTTP deadline โ€” it is applied to both the `aiohttp.ClientSession`
  (covering connect + read idle time) and to the per-call `timeout=`
  override on every `session.post(...)`, so the same value governs the
  blocking `run()` path **and** the streaming `astream()` path. The
  previous hard-coded `ClientTimeout(total=600)` is gone from the
  call sites.
- `runtime_components.py`: `Generate.astream()` and `AsyncTokenStream`
  accept an optional `on_token` callback fired for every token as it
  arrives. The callback is sync (it should be a fast local write;
  blocking work belongs in a separate coroutine that drains the
  iterator normally) and is invoked *before* the token is appended to
  `AsyncTokenStream.text`, so the consumer sees the same string the
  iterator returns.
- `runtime_components.py`: `Generate._astream_http()` accepts an
  optional `on_parse_error` callback. When `json.loads` fails on a
  `data:` SSE chunk (or the chunk has an unexpected shape), the raw
  payload is forwarded to the callback instead of being silently
  dropped. `Generate.astream()` plumbs the parameter through to the
  HTTP backend.
- `si1.py`: Chaos-phase tokens now stream to stdout in typewriter
  style. Each token is forwarded through `Speak.run` (single
  `to_thread` write+flush, so output remains ordered even if other
  coroutines later race) and the final mutation is printed in full by
  the existing `await self.speaker.run(proposed)` at the end of
  `run_iteration`. The user sees Lucifer's chaos-phase reasoning as
  it arrives, then the gate-accepted final response on its own block.
- `si1.py`: Each of the four duel phases (chaos / discipline / refine
  / gate) is now wrapped in its own
  `try/except (aiohttp.ClientError, asyncio.TimeoutError)`. A network
  failure on any single phase is logged as `duel_phase_failed` (with
  the phase name) and recorded in `duellog.json` as
  `kind="<phase>_failure"`, and the loop returns `(None, None)` so
  `run_iteration` surfaces the existing fallback. A crashed llama-server
  no longer takes the runtime down with a traceback.
- `si1.py`: Chaos-phase SSE parse errors are forwarded to
  `duel_log.record(..., kind="stream_parse_error", text=raw[:200])` via
  the new `on_parse_error` hook. Operators can now spot malformed
  streaming output without reading the runlog's redacted summaries.

### Fixed
- `si1.py`: The chaos-phase block had `async with self.lucifer:`
  bracketing only the first HTTP call. The session was closed at the
  end of the chaos phase, then the subsequent revise / critique / gate
  calls (all of which use the same `Generate` instance) ran on a
  closed `aiohttp.ClientSession`. The previous code only worked by
  accident. The `async with` is removed from
  `_generate_with_observer`; session ownership now lives entirely in
  `amain()`, which already opens both Lucifer and Obi sessions with
  one long-lived `async with runtime.lucifer, runtime.obi.generate:`.
- `memory_store.py`: `MemoryStore.load()` and `save()` previously used
  `asyncio.gather(...)` without `return_exceptions=True`. A single
  corrupted file (e.g. a truncated `facts.json` from a previous
  crash) aborted the whole boot or lost the runtime counter on save.
  Both calls now pass `return_exceptions=True`; failed loads surface
  as `None` for that file, failed saves are logged at the call site
  rather than crashing the iteration.

### Changed
- `si1.py`: Chaos-phase token collection switched from
  `draft += token` (O(nยฒ) reallocation) to `tokens.append(token)` +
  `draft = "".join(tokens)` (O(n) overall). Removes the only
  quadratic-cost string operation in the hot path. A blank line is
  emitted at the end of the chaos stream via `Speak.run("")` so the
  gate-accepted response that follows starts on its own visual block.
- `runtime_components.py`: `_astream_http` now uses the same per-call
  `ClientTimeout(total=self._timeout_s)` override as `_run_http`,
  instead of relying on the session's default. Streaming is the path
  that most needs a deadline โ€” a hung socket previously had no
  surface until the session-level `total` fired.
- `runtime_components.py`: `_astream_http` collapses the previously
  split `except json.JSONDecodeError` + `except (KeyError, IndexError,
  TypeError)` into a single `except (...)` block. The same error
  handling path is reached for either case and the optional
  `on_parse_error` callback is the single point of observability.

### Verified
- `python3 -m py_compile si1.py runtime_components.py models.py
  memory_store.py logger.py prompt_engine.py fact_extractor.py
  fact_validator.py config.py` โ’ 0 errors.
- `Generate(http_url=...)` with no `timeout_s` โ’ `_timeout_s == 600.0`
  (backwards compatible).
- `Generate(..., timeout_s=42.0)` โ’ `_timeout_s == 42.0` and the value
  is propagated to both the session default and the per-call timeout.
- `AsyncTokenStream` with `on_token=seen.append` fires the callback
  for every token in order, before the token is appended to
  `self.text`, and the final `text` matches the joined tokens.
- `Generate.astream` signature carries both `on_token` and
  `on_parse_error` parameters.
- `_generate_with_observer` with a `Generate` that raises
  `aiohttp.ClientError` on `astream` returns `(None, None)` (and emits
  a `duel_phase_failed` log entry) instead of propagating the
  exception. The runtime no longer dies when llama-server is down.

## [2026-07-26] โ€” Async runtime stabilization + duel-loop wiring + boot banner

### Added
- `si1.py`: Boot banner printed at the top of `build_runtime()`. Shows `config.APP_NAME`, `config.RUNTIME_VERSION`, memory load status (`loaded` / `error` with exception repr), live counts (`facts=N, archive=N, turn=N`), per-file presence + size for `runtime.json` / `facts.json` / `archive.json` / `runlog` / `duellog`, and the model name + URL for both Lucifer (port 666) and Obi (port 999). Missing files are reported as `missing (will be created on first save)` rather than crashing; unreadable files are reported as `unreadable: <error>`. The banner prints before the runtime is returned, so it appears the moment `si1.py` starts โ€” before the `> ` prompt.

## [2026-07-26] โ€” Async runtime stabilization + duel-loop wiring

### Fixed
- `memory_store.py`: `MemoryStore.load()` and `MemoryStore.save()` were calling `RuntimeState.from_raw()` / `to_raw()` and `Fact.from_raw()` / `to_raw()`, but those methods don't exist on the dataclasses. The runtime crashed at startup with `AttributeError`. Renamed all four call sites to the actual API: `from_dict` / `to_dict`. `MemoryStore` now loads and saves cleanly.
- `models.py`: `RuntimeState` was missing the `turn` and `last_active_at` fields that the async runtime writes on every iteration (`self.runtime.turn += 1`, `self.runtime.last_active_at = ...`). The runtime crashed with `AttributeError: 'RuntimeState' object has no attribute 'turn'` on shutdown. Both fields added with safe defaults; `from_dict` reads them with `.get(..., default)` so older on-disk JSON files still load.
- `models.py`: `MemoryDelta.compare` computed the delta but never returned it (the `return cls(...)` line was missing). The runtime silently produced empty deltas. Added the missing return.
- `models.py`: `MemoryDelta.modified_facts` was declared with `field(default_factory=dict)` but the type annotation said `list[dict[str, Any]]`. Changed the annotation to `dict[str, Any]` to match the factory.
- `si1.py`: The chaos-phase block in `_generate_with_observer` had broken indentation โ€” `draft = ""`, `async for token in stream`, and the `duel_log.record` / `logger.log` calls leaked out of the `async with self.lucifer:` context. The `async for` ran after the aiohttp session was closed, and the log lines referenced an undefined `draft_result`. Re-indented the whole block to stay inside `async with self.lucifer:` and replaced the missing `draft_result` with `stream.finalize()` (the `AsyncTokenStream` wrapper already exposes `finalize()` returning a `GenerationResult` with `elapsed_s`).
- `models.py`: Six duel-loop symbols (`DuelLogEntry`, `DuelVerdict`, `GatePayload`, `find_aligned_payload`, `find_override`, `AlignedMeta`, plus `HOOK_NAMES`) were defined only in `models.bak.py` but imported via `import models as M` from `runtime_components.py` and `si1.py`. The runtime crashed the moment the duel loop reached `M.DuelVerdict.from_gate_text(...)`. Promoted all six symbols into the canonical `models.py` and deleted `models.bak.py` so it can't be re-imported by mistake.

### Changed
- `runtime_components.py`: `ObserverV2.__init__` now loads **both** `core/system.md` (the runtime identity) and `core/observer_system.md` (Obie's constitutional role) and concatenates them with a blank line. Previously Obi only saw his own observer prompt; now he sees the full SI-1 identity first, then his role definition. The constructor gained an optional `observer_system_prompt_path` parameter for testing; existing call sites in `si1.py` (`ObserverV2(obi_gen)`) work unchanged. If either file is missing, that section is silently empty rather than raising.
- `runtime_components.py`: `Generate.astream()` and `AsyncTokenStream` are now the canonical streaming path for the chaos phase. `AsyncTokenStream.finalize()` returns a `GenerationResult` with `elapsed_s` so the runtime can log first-token-to-last-token latency without a separate non-streaming call.

### Verified
- `python -c "import si1; import runtime_components; import memory_store; import logger; import prompt_engine; import fact_extractor; import fact_validator; print('all 7 modules import OK')"` โ’ exit code 0.
- `python -c "import asyncio; from si1 import build_runtime; asyncio.run(build_runtime())"` โ’ constructs cleanly, both `Generate` instances configured for `LUCIFER_URL` (port 666) and `OBI_URL` (port 999), `RuntimeState.turn == 0`, `len(facts) == 0`, `len(archive) == 0`.
- `ObserverV2.system_prompt` length is 19,670 chars after the dual-prompt change (was ~3,000 before); first 200 chars begin with the `system.md` header, last 200 chars end with the `observer_system.md` closing paragraph.
- `models.bak.py` deleted from disk; `ls` confirms only `models.py` remains.

## [2026-07-22] โ€” Async runtime bugfixes

### Fixed
- `si1.py`: `run_iteration` was passing `(self.runtime, self.facts)` to `PromptEngine.build_context_block`, but the method's signature is `(self, memory: MemorySnapshot)`. The previous code raised `TypeError` (or silently mis-assembled the prompt) on every turn. Now constructs a real `M.MemorySnapshot(runtime=..., facts=..., archive=...)` and passes that.
- `si1.py`: `run_iteration` re-read the system prompt from disk on every iteration via a separate `asyncio.gather` task, even though `PromptEngine.__init__` already loads it once. The redundant read could also disagree with the prompt actually built by the engine. Removed the per-turn read; `PromptEngine` now owns the system prompt for the lifetime of the session.
- `si1.py`: Observer retry was a no-op โ€” it called `generate.run(prompt)` again with the *same* prompt, ignoring the observer's `score` and `reason`. Replaced with a bounded loop (`MAX_OBSERVER_RETRIES = 2`) that injects the observer's feedback into the next prompt and accepts only when both `accept=True` and `score >= OBSERVER_ACCEPT_SCORE` (0.6). On exhaustion the runtime now logs `observer_exhausted` and surfaces a clear fallback string instead of silently returning the rejected output.
- `si1.py`: `RuntimeState.last_input` and `last_output` were never written by the async runtime, so the next turn's context block always showed stale data. Both fields are now updated each iteration.
- `si1.py`: `ArchiveManager` was instantiated and stored but never called โ€” `self.archive` was never appended to, so persisted archives never grew. The runtime now calls `archiver.summarize(...)` + `archiver.append(...)` after every turn. Failures are caught and logged as `archive_failed` so a broken summary path can never break an iteration.

### Changed
- `prompt_engine.py`: `PromptEngine.build(user_input, memory)` split into `build(system_prompt, context_block, user_input)`. The engine now receives pre-built pieces from the runtime instead of re-reading the snapshot's structure. The system prompt defaults to the value loaded at construction if the caller passes an empty string.
- `runtime_components.py`: `Speak.run()` now does write+flush in a single `to_thread` call (was two), halving thread hops and preventing output desync if multiple `Speak` coroutines ever race.
- `runtime_components.py`: `Generate._astream_llama_cpp` rewritten as a real async bridge. The blocking `llm.create_chat_completion(..., stream=True)` call now runs on the default executor; tokens are forwarded to the async consumer via `loop.call_soon_threadsafe(queue.put_nowait, delta)`, with a `None` sentinel marking end-of-stream and a `BaseException` payload for producer errors. The event loop stays free during first-token latency and `task.cancel()` now works mid-stream.
- `si1.py`: Added module-level constants `MAX_OBSERVER_RETRIES = 2` and `OBSERVER_ACCEPT_SCORE = 0.6` so the retry policy is visible at the top of the file.
- `si1.py`: Removed unused `from pathlib import Path` import (the system-prompt read that needed it was deleted).

### Verified
- All touched files cross-checked structurally: imports, `MemorySnapshot` field defaults, `ArchiveEntry(time=, summary=)` field names, and `PromptEngine.build` call sites.
- No real Python interpreter is available in this environment, so `python -m py_compile` was not run. Run it locally before deploying.

## [Unreleased]

### Pending โ€” Option B (Local llama-cpp-python binding)
- Install `llama-cpp-python` and `requests` into the venv at `c:\Users\Timm\Desktop\SI-1\.venv\`.
- Set `SI1_LLAMA_MODEL` to `e:\SI-1\models\HERETICODER-2.5-3B-IT.i1-Q6_K.gguf` and `SI1_LLAMA_THREADS=8`.
- Restore `Speak.run()` to print model output (currently `pass`).
- Switch `LLM_BACKEND` from `"llama_cpp"` (in-process binding) to `"legacy_http"` once the local binding is verified, or keep `"llama_cpp"` and ensure the model path resolves.
- Note: `llama-cpp-python` requires C++ build tools on Windows; expect a 5โ€“10 minute compile or use a pre-built wheel.

## [2026-07-16] โ€” HTTP backend patch (Option A)

### Changed
- `runtime_components.py`: `Generate` now supports an HTTP backend that talks to the running `llama-server` at `http://127.0.0.1:8080` (OpenAI-compatible `/v1/chat/completions`). Selected automatically when `LLM_BACKEND == "legacy_http"` or when the in-process `llama_cpp` binding fails to initialize.
- `runtime_components.py`: `Speak.run()` now prints model output (was a no-op `pass`).
- `config.py`: `LLM_BACKEND` default remains `"llama_cpp"`; the HTTP path activates as a fallback so the existing config does not need to change.

### Fixed
- Silent generation failures: when the in-process `llama_cpp` binding is unavailable, the HTTP fallback now produces visible output instead of returning an error string that was swallowed by `Speak`.
- Observer and Memorize internal `Generate` calls now route through the same backend-aware path.

### Verified
- `llama-server` running at `http://127.0.0.1:8080` with `HERETICODER-2.5-3B-IT.i1-Q6_K.gguf` loaded.
- `build_runtime()` constructs successfully.
- `si1.py` exits cleanly (exit code 0) and now streams model output to the terminal.

## [2026-07-23] - Four-phase duel loop + ObserverV2 + two-server topology

### Added
- `models.py`: `DuelLogEntry` (ts, turn, round, kind, actor, text, meta) and `DuelVerdict` (accepted, reason, with `from_gate_text` classmethod) dataclasses. The gate parser tolerates casing, blank lines, and the alternative `reason - ...` form.
- `logger.py`: `DuelLog` class. Async, lock-guarded JSONL writes to `config.DUEL_LOG_FILE` (`./logs/duellog.json`). No redaction - this is the auditor's source of truth. `record(turn, round, kind, actor, text, **meta)` is the single entry point.
- `config.py`: `LUCIFER_URL` (port 666) and `OBI_URL` (port 999), per-role sampling dicts (`LUCIFER_SAMPLING`, `OBI_SAMPLING_CRITIQUE`, `OBI_SAMPLING_GATE`), `OBI_SYSTEM_PROMPT_FILE`, `DUEL_LOG_FILE`, `MAX_DUEL_ROUNDS = 1` (was 2; pinned to single-round loop), `ALIGNED_TOKEN = "[ALIGNED]:"`.
- `core/observer_system.md`: New system prompt for Obi, framing him as Lucifer's older brother and mentor. Includes the four-hook critique contract and the strict `ACCEPTED` / `REJECT\nreason: ...` gate format.
- `si1.py`: `_generate_with_observer` is now the true four-phase loop (Chaos -> Discipline -> Refined Learning -> Final Peripheral Gate). The runtime swaps Obi's sampling to the deterministic gate profile for the gate call and restores it after.
- `si1.py`: `build_runtime` constructs two independent `Generate` instances (Lucifer on 666, Obi on 999) and wires them correctly: `ObserverV2` gets Obi's generator; `Memorize` and `ArchiveManager` get Lucifer's.

### Renamed
- `runtime_components.py`: `ObserverV1` -> `ObserverV2`. The "V1" was the JSON-output-validator design; V2 is the sibling-mentor, free-text design. The class keeps the `critique()` and `gate()` methods (no logic change, only the name and docstring).

### Fixed
- `models.py`: Trailing stray `)` after `MemorySnapshot` removed. File now compiles.
- `runtime_components.py`: `Generate.__init__` was referencing undefined parameters (`temperature`, `top_p`, etc.) and a non-existent `config.RUNTIME_MODEL`. Replaced with a clean signature: `__init__(backend, http_url, model, sampling, llama_cpp_path, llama_cpp_threads)`. Sampling is now passed as a dict from config so each role gets its own profile.
- `runtime_components.py`: `Update.run` was saving twice in a row (paste artifact). Reduced to a single save call.
- `runtime_components.py`: `from pathlib import Path` import added; `ObserverV2.__init__` uses it to load Obi's system prompt.
- `si1.py`: `amain()` now uses `runtime.lucifer` (was `runtime.generate`); the duplicate `main()` call at the bottom of the file removed.
- `si1.py`: Stale `MAX_OBSERVER_RETRIES` and `OBSERVER_ACCEPT_SCORE` constants removed (JSON-validator era). `runtime_start` log now reports `lucifer_model`, `obi_model`, `lucifer_url`, `obi_url`, and `max_duel_rounds` instead of the non-existent `config.RUNTIME_MODEL`.
- `docs/architecture.md`: Removed references to deleted `core/protocol.md` and `core/abstract.md`. Added sections describing the four-phase loop, the two-server topology, and the memory/logging split.

### Verified
- `python -m py_compile *.py` -> 0 errors across all 9 .py files.
- `python -c "import si1"` -> all symbols resolve (`ObserverV2`, `Generate`, `DuelLog`, `DuelLogEntry`, `DuelVerdict`, `SI1Runtime`, `build_runtime`).
- Three end-to-end scenarios on `_generate_with_observer` with scripted fakes: (A) first-round ACCEPT, (B) second-round ACCEPT after first REJECT, (C) hard REJECT after two failed rounds. All three passed.
