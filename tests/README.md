# SI-1 Test Suite

Two test modules live in this folder. Both are pure-Python, no LLM
server required.

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

## `test_smoke_tests.py` — messages pipeline, ThoughtRouter, Speak

The original six smoke tests, refactored to run on POSIX paths and
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

## Running

```bash
# From the repo root
python -m unittest tests.test_loop_structure -v
python -m unittest tests.test_smoke_tests -v

# Or with pytest, if installed
pytest tests/ -v
```

All 17 tests pass on Linux.
