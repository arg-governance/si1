# SI-1 Test Suite

Three test modules live in this folder. They are pure-Python and do not
require a live LLM server.

## `test_loop_structure.py` — pin the single-round four-phase contract

This is the test suite that codifies the three rules the Architect
asked for:

1. **Only 1 round per loop.** `config.MAX_DUEL_ROUNDS == 1`. The
   for-loop over `MAX_DUEL_ROUNDS` in `si1.py` is gone.
2. **Only 1 loop with 4 steps.** The four phases (Chaos, Discipline,
   Refine, Gate) each appear as a straight-line sequence inside
   `_generate_with_observer`, never wrapped in a round iterator.
3. **Lucifer's DRAFT is what Obi critiques.** `critique_stream` is
   called with `draft=draft` (the chaos-phase output). The revise
   phase uses that DRAFT as the conversation history, not a
   regenerated text. Obi is not invoked in the refine phase.

It also pins the duellog kinds (chaos→`draft`, refine→`mutation`)
so a future change can't silently re-introduce a "re-draft inside the
loop" pattern.

11 tests, all AST-based — they walk the source tree, so the suite
will fail loudly if someone reintroduces the runaway loop.

## `test_smoke_tests.py` — messages pipeline, tools, ThoughtRouter, Speak

Smoke tests for the messages pipeline, tool handling, and gate behavior, refactored to run on POSIX paths and
to import from `runtime_components` (the Generate class was moved
out of the standalone `generate.py` module some time ago). They
cover:

- `PromptEngine.build_messages` returns a valid ChatML list
- The si1.py runtime uses `build_messages` and logs all four
  phase-done events
- `ThoughtRouter` routes Gemma-4 `<|channel>thought` content
- `Speak.open_thought / write_thought / close_thought` emit the
  marker / ANSI codes
- End-to-end message structure: chaos (2 msgs) and refine (5 msgs,
  multi-turn)
- Non-streaming tool-call replay and streaming tool-call execution/replay
- Direct-tag reserved-marker sanitization and tool availability settings
- Gate-input JSON framing with hostile instruction/fake-verdict content
- Boxed visibility for all four phases on accept and reject
- Post-hoc gate verdict and runtime evidence visibility
- Aligned token and next-line payload parsing
- SQL logger construction and query smoke coverage

## `test_memory_store.py` — atomic persistence

These tests verify that a successful save replaces valid JSON files and leaves
no temporary files behind, and that a failed atomic replacement preserves the
previous file and is surfaced to the caller.

## Running

```bash
# From the repo root
python -m unittest tests.test_loop_structure -v
python -m unittest tests.test_smoke_tests -v

# Or with pytest, if installed
pytest tests/ -v
```

Run all three modules with:

```bash
python -m unittest tests.test_loop_structure tests.test_smoke_tests tests.test_memory_store -v
```
