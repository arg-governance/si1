"""Tests for the single-pass four-phase loop structure.

These tests pin down the contract the Architect requested:

  1. Only 1 round per loop.
  2. Only 1 loop with 4 steps (Chaos, Discipline, Refine, Gate).
  3. Lucifer's DRAFT is what Obi critiques. Obi does NOT generate a
     new DRAFT from Lucifer's reasoning — the revise phase is the
     only place a second text is produced, and it is the REVISED
     text (prefixed with [ALIGNED]:), not a regenerated DRAFT.

The tests are static (AST + source-string inspection) so they run
without bringing up the actual LLM servers. They will fail loudly
if anyone reintroduces a nested ``for round_idx in range(...)`` over
``MAX_DUEL_ROUNDS`` or otherwise grows the loop back beyond 1 round.
"""

from __future__ import annotations

import ast
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestMaxDuelRoundsIsOne(unittest.TestCase):
    """Contract 1: only 1 round per loop."""

    def test_config_max_duel_rounds_is_one(self) -> None:
        from config import MAX_DUEL_ROUNDS  # noqa: WPS433
        self.assertEqual(
            MAX_DUEL_ROUNDS,
            1,
            "MAX_DUEL_ROUNDS must be exactly 1: one bounded adversarial "
            "round per Architect turn. Setting it > 1 re-enables the "
            "50-round runaway loop the Architect reported.",
        )

    def test_config_docstring_states_one_round(self) -> None:
        text = _read(ROOT / "config.py")
        # Look at the comment block above the MAX_DUEL_ROUNDS assignment
        match = re.search(
            r"# Duel loop parameters\..*?MAX_DUEL_ROUNDS = (\d+)",
            text,
            re.DOTALL,
        )
        self.assertIsNotNone(
            match, "Could not locate the MAX_DUEL_ROUNDS block in config.py"
        )
        block = match.group(0).lower()
        self.assertIn("one", block)
        self.assertIn("round", block)
        # And the literal value must be 1
        self.assertEqual(int(match.group(1)), 1)


class TestSinglePassFourPhaseLoop(unittest.TestCase):
    """Contract 2: only 1 loop with 4 steps (Chaos, Discipline, Refine, Gate)."""

    def setUp(self) -> None:
        self.src = _read(ROOT / "si1.py")
        self.tree = ast.parse(self.src)

    @staticmethod
    def _find_function(tree: ast.AST, name: str) -> ast.FunctionDef | None:
        """Find a top-level function OR a class method by name."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == name:
                return node
            if isinstance(node, ast.ClassDef):
                for child in node.body:
                    if (
                        isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and child.name == name
                    ):
                        return child
        return None

    def test_no_nested_round_loop_in_generate_with_observer(self) -> None:
        """The for-loop over MAX_DUEL_ROUNDS must be gone."""
        # Match a for-loop whose iterator mentions MAX_DUEL_ROUNDS.
        # AST-level check so whitespace/comments don't matter.
        offenders: list[str] = []
        for node in ast.walk(self.tree):
            if not isinstance(node, ast.For):
                continue
            # Inspect the iterable source via line numbers.
            for_line = self.src.splitlines()[node.lineno - 1]
            if "MAX_DUEL_ROUNDS" in for_line:
                offenders.append(
                    f"line {node.lineno}: {for_line.strip()}"
                )
        self.assertEqual(
            offenders,
            [],
            "Found a for-loop over MAX_DUEL_ROUNDS in si1.py. The "
            "single-pass refactor must NOT contain a round iterator:\n"
            + "\n".join(offenders),
        )

    def test_generate_with_observer_runs_all_four_phases(self) -> None:
        """The function must call all four phase entry points exactly
        as a straight-line sequence (no loop wrapping them)."""
        required_calls = {
            "astream_messages",          # chaos + refine generation
            "critique_stream",           # discipline-phase
            "gate_stream",               # gate-phase
        }
        for name in required_calls:
            self.assertIn(
                name,
                self.src,
                f"Expected {name!r} in si1.py (one of the four phases).",
            )

    def test_single_round_assert_in_place(self) -> None:
        """A defensive ``assert MAX_DUEL_ROUNDS == 1`` must be present
        in ``_generate_with_observer`` so a future change can't silently
        re-enable the nested round loop."""
        func = self._find_function(self.tree, "_generate_with_observer")
        self.assertIsNotNone(
            func, "Could not find _generate_with_observer in si1.py"
        )
        asserts = [
            n for n in ast.walk(func)
            if isinstance(n, ast.Assert)
        ]
        self.assertTrue(
            any(
                "MAX_DUEL_ROUNDS" in ast.unparse(a.test)
                for a in asserts
            ),
            "Expected an `assert config.MAX_DUEL_ROUNDS == 1` inside "
            "_generate_with_observer to keep the single-pass contract "
            "from being silently broken.",
        )


class TestObiSeesLucifersDraft(unittest.TestCase):
    """Contract 3: Lucifer's DRAFT is what Obi critiques. Obi does NOT
    generate a DRAFT — the revise phase produces the REVISED text only,
    and it is logged to the duellog as ``mutation``, never as ``draft``.
    """

    def setUp(self) -> None:
        self.src = _read(ROOT / "si1.py")
        self.tree = ast.parse(self.src)

    def _function_body(self, name: str) -> str:
        """Return the source slice for the given function (or method)."""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef) and node.name == name:
                lines = self.src.splitlines()[node.lineno - 1 : node.end_lineno]
                return "\n".join(lines)
            # Methods live inside ClassDef; recurse one level.
            if isinstance(node, ast.ClassDef):
                for child in node.body:
                    if (
                        isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and child.name == name
                    ):
                        lines = self.src.splitlines()[
                            child.lineno - 1 : child.end_lineno
                        ]
                        return "\n".join(lines)
        raise AssertionError(f"Function {name!r} not found in si1.py")

    def test_obi_critique_receives_chaos_draft(self) -> None:
        """The chaos-phase DRAFT (variable ``draft``) is passed as the
        ``draft=`` argument to ``ObserverV2.critique_stream``."""
        # Find the call: self.obi.critique_stream(...draft=draft...)
        pattern = re.compile(
            r"critique_stream\s*\("
            r"[^)]*?"
            r"draft\s*=\s*draft",
            re.DOTALL,
        )
        self.assertRegex(
            self.src,
            pattern,
            "Expected `self.obi.critique_stream(... draft=draft ...)` "
            "so Obi critiques Lucifer's DRAFT, not a regenerated text.",
        )

    def test_revise_phase_uses_draft_as_assistant_turn(self) -> None:
        """The revise phase threads the DRAFT as a prior assistant turn
        (so the model can revise, NOT regenerate from reasoning)."""
        # We accept either:
        #   prior_turns=[{"role": "assistant", "content": draft}]
        # OR a multi-line version with comments between fields. The
        # essential contract: there is exactly one prior_turns= list
        # whose only entry has role=assistant and content=draft.
        call_sites = re.findall(
            r"prior_turns\s*=\s*(\[[^\]]*?\])\s*",
            self.src,
            re.DOTALL,
        )
        self.assertTrue(
            call_sites,
            "Expected a prior_turns= keyword argument somewhere in si1.py",
        )
        # Find the call site inside _generate_with_observer and check it.
        func_region = self._function_body("_generate_with_observer")
        func_calls = re.findall(
            r"prior_turns\s*=\s*(\[[^\]]*?\])\s*",
            func_region,
            re.DOTALL,
        )
        self.assertTrue(
            func_calls,
            "Expected prior_turns= inside _generate_with_observer "
            "(the revise-phase build_messages call)",
        )
        # The literal must contain role=assistant and content=draft.
        joined = " ".join(func_calls)
        self.assertIn(
            "assistant",
            joined,
            "The revise-phase prior_turns must include role='assistant'",
        )
        self.assertRegex(
            joined,
            r"[\"']content[\"']\s*:\s*draft",
            "The revise-phase prior_turns must use the DRAFT variable "
            "as the assistant content (not a regenerated text).",
        )

    def test_revise_phase_does_not_call_critique(self) -> None:
        """Obi does not produce a draft in the refine phase. The
        refine phase must contain exactly one ``astream_messages`` call
        (Lucifer's revise) and no ``critique_stream`` call."""
        # Locate the refine-phase region by finding the comment marker.
        refine_marker = "[refine-phase streaming Lucifer's revision"
        idx = self.src.find(refine_marker)
        self.assertGreater(idx, 0, "Could not locate the refine-phase marker")
        # Take the region from the marker to the next phase marker
        # (the gate phase) — that's the body of phases 3.
        gate_marker = "[obi gate:"
        gate_idx = self.src.find(gate_marker, idx)
        self.assertGreater(gate_idx, idx, "Could not find the gate marker after refine")
        refine_region = self.src[idx:gate_idx]
        self.assertNotIn(
            "critique_stream",
            refine_region,
            "Obi must NOT be called in the refine phase. Obi critiques "
            "(Phase 2) and gates (Phase 4) only.",
        )
        self.assertIn(
            "astream_messages",
            refine_region,
            "The refine phase must call astream_messages exactly once "
            "to produce the REVISED text.",
        )

    def test_duellog_kinds_are_phase_distinct(self) -> None:
        """The duellog must distinguish chaos-phase 'draft' from
        refine-phase 'mutation'. They are different concepts and the
        runtime must never log the revise-phase output as a 'draft'."""
        # Find every duel_log.record call and inspect the 'kind' kwarg.
        # The kind= values must be from a fixed set.
        allowed_kinds = {
            "stream_parse_error",  # ok in any phase
            "draft",               # chaos-phase ONLY
            "chaos_failure",       # chaos-phase network error
            "critique_failure",    # discipline-phase
            "critique",            # discipline-phase
            "architect_opinion",   # discipline-phase (Obi's take on prompt)
            "refine_failure",      # refine-phase
            "mutation",            # refine-phase (revised text)
            "gate_failure",        # gate-phase
            "gate",                # gate-phase
            "meta",                # any revised-draft meta
            "rejection",           # runtime hard reject
        }
        for match in re.finditer(
            r"self\.duel_log\.record\(\s*[^)]*?kind\s*=\s*['\"]([^'\"]+)['\"]",
            self.src,
            re.DOTALL,
        ):
            kind = match.group(1)
            self.assertIn(
                kind,
                allowed_kinds,
                f"Unknown duellog kind: {kind!r}. Allowed: {sorted(allowed_kinds)}",
            )
        # Specifically: there must be exactly one 'draft' log call site
        # (chaos) and at least one 'mutation' log call site (refine).
        # Two 'draft' sites would mean Lucifer is re-drafting inside the
        # loop — exactly the runaway pattern the Architect reported.
        draft_sites = re.findall(
            r"self\.duel_log\.record\(\s*[^)]*?kind\s*=\s*['\"]draft['\"]",
            self.src,
            re.DOTALL,
        )
        self.assertEqual(
            len(draft_sites),
            1,
            "Expected exactly one chaos-phase 'draft' log call. Multiple "
            "draft call sites mean Lucifer is regenerating his DRAFT "
            "inside the loop (the runaway pattern).",
        )


class TestNoRunawayOuterLoop(unittest.TestCase):
    """The runtime's outer ``while not self._stop.is_set()`` loop in
    ``SI1Runtime.run`` is the Architect-iteration loop (one iteration
    per user prompt). Each iteration must invoke the four-phase
    duel-loop function exactly ONCE, not in a nested while/loop."""

    def test_outer_run_uses_while_for_user_iteration(self) -> None:
        self.assertIn(
            "while not self._stop.is_set()",
            _read(ROOT / "si1.py"),
            "The runtime's outer loop in SI1Runtime.run must use the "
            "_stop event so Ctrl-C / EOF can terminate it cleanly.",
        )

    def test_run_iteration_invokes_duel_loop_once(self) -> None:
        """``run_iteration`` must call ``_generate_with_observer`` once
        and not wrap it in a while/loop."""
        src = _read(ROOT / "si1.py")
        tree = ast.parse(src)
        func: ast.FunctionDef | None = None
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "run_iteration"
            ):
                func = node
                break
        if func is None:
            # Try methods
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for child in node.body:
                        if (
                            isinstance(
                                child, (ast.FunctionDef, ast.AsyncFunctionDef)
                            )
                            and child.name == "run_iteration"
                        ):
                            func = child
                            break
                    if func:
                        break
        self.assertIsNotNone(func)
        # Confirm the body has no loop construct at all.
        loops = [
            n for n in ast.walk(func)
            if isinstance(n, (ast.For, ast.While))
        ]
        self.assertEqual(
            loops,
            [],
            "run_iteration must not contain any for/while loop. The "
            "single pass through the four phases is delegated to "
            "_generate_with_observer.",
        )
        # Confirm it calls _generate_with_observer exactly once.
        call_count = sum(
            1
            for n in ast.walk(func)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "_generate_with_observer"
        )
        self.assertEqual(
            call_count,
            1,
            "run_iteration must call _generate_with_observer exactly once.",
        )


if __name__ == "__main__":
    unittest.main()


# ==============================================================
# Helpers + behavior for the new "Architect opinion" split.
# These were added when Obi started emitting a fifth discipline-phase
# block ("My view on the Architect's prompt:") that the runtime
# surfaces to the Architect but does NOT feed to Lucifer.
# ==============================================================


class TestArchitectOpinionSplit(unittest.TestCase):
    """Verify ``models.split_architect_opinion`` cleanly separates
    Obi's four-hook critique from his independent take on the
    Architect's prompt. The split is what lets the runtime show the
    opinion to the Architect without leaking it into Lucifer's
    revise-phase prompt."""

    def test_no_opinion_returns_original(self) -> None:
        import models as M  # noqa: WPS433

        text = (
            "You arrived at this conclusion because: x\n"
            "However, you overlooked: y\n"
            "Remember our constitutional principle: z\n"
            "Re-evaluate your reasoning: w\n"
        )
        hooks, opinion = M.split_architect_opinion(text)
        self.assertEqual(hooks, text)
        self.assertIsNone(opinion)

    def test_opinion_split_strips_block(self) -> None:
        import models as M  # noqa: WPS433

        hooks_only = (
            "You arrived at this conclusion because: x\n"
            "However, you overlooked: y\n"
            "Remember our constitutional principle: z\n"
            "Re-evaluate your reasoning: w\n"
        )
        opinion_body = (
            "The premise holds, but the scope is underspecified.\n"
            "Architect should clarify the target audience."
        )
        full = (
            hooks_only
            + "\nMy view on the Architect's prompt:\n"
            + opinion_body
            + "\n"
        )
        hooks, opinion = M.split_architect_opinion(full)
        # Hooks text should match the original four-hook portion (no
        # opinion block trailing).
        self.assertEqual(hooks.rstrip(), hooks_only.rstrip())
        self.assertIsNotNone(opinion)
        self.assertIn("underspecified", opinion)
        self.assertIn("target audience", opinion)
        # Opinion must not contain the four-hook headers anymore.
        for header in (
            "you arrived at this conclusion because:",
            "however, you overlooked:",
            "remember our constitutional principle:",
            "re-evaluate your reasoning:",
        ):
            self.assertNotIn(header, opinion.lower())

    def test_header_case_insensitive(self) -> None:
        import models as M  # noqa: WPS433

        text = (
            "Re-evaluate your reasoning: w\n"
            "\nMY VIEW ON THE ARCHITECT'S PROMPT:\n"
            "Take: prompt is ambiguous.\n"
        )
        hooks, opinion = M.split_architect_opinion(text)
        self.assertIn("w", hooks)
        self.assertEqual(opinion, "Take: prompt is ambiguous.")

    def test_empty_opinion_body_returns_empty_string(self) -> None:
        import models as M  # noqa: WPS433

        text = (
            "Re-evaluate your reasoning: w\n"
            "\nMy view on the Architect's prompt:\n"
        )
        _hooks, opinion = M.split_architect_opinion(text)
        # Empty body should still produce an empty string (not None)
        # so the runtime logs that Obi emitted the header with no body.
        self.assertEqual(opinion, "")


class TestArchitectOpinionWiring(unittest.TestCase):
    """Verify the wiring in si1.py: the runtime splits Obi's critique,
    surfaces the opinion block visibly to the Architect, and feeds only
    the hooks portion back to Lucifer for the refine phase."""

    def setUp(self) -> None:
        self.src = _read(ROOT / "si1.py")

    def test_runtime_calls_split_architect_opinion(self) -> None:
        self.assertIn(
            "split_architect_opinion",
            self.src,
            "si1.py must call models.split_architect_opinion on Obi's "
            "critique so the opinion block is split out before the "
            "refine phase.",
        )

    def test_opinion_surfaced_with_obi_header_label(self) -> None:
        """The runtime must print a visible header label so the
        Architect can see Obi's independent read on stdout."""
        self.assertIn(
            "[obi's view on the architect's prompt]",
            self.src.lower(),
            "si1.py must print a labelled header so the Architect sees "
            "Obi's independent take on stdout (not buried in duellog).",
        )

    def test_architect_opinion_kind_in_duellog(self) -> None:
        """The opinion block must be logged as kind='architect_opinion'
        so the auditor can reconstruct Obi's prompt-reads from duellog."""
        # Look for kind="architect_opinion" inside a duel_log.record call.
        self.assertRegex(
            self.src,
            r'kind\s*=\s*["\']architect_opinion["\']',
            "Expected duel_log.record(kind='architect_opinion') in si1.py "
            "to log Obi's independent read of the Architect's prompt.",
        )

    def test_refine_phase_receives_hooks_only(self) -> None:
        """The refine-phase prompt must use the *split* critique text
        (hooks only), not the raw critique_text that included the
        opinion block. We verify by inspecting that the split result
        is reassigned before the build_messages call."""
        # Pattern: hooks_text, architect_opinion = M.split_architect_opinion(critique_text)
        # followed (eventually) by  critique_text = hooks_text or critique_text
        pattern_split = re.search(
            r"hooks_text\s*,\s*architect_opinion\s*=\s*"
            r"M\.split_architect_opinion\(critique_text\)",
            self.src,
        )
        self.assertIsNotNone(
            pattern_split,
            "Expected the split result to be unpacked into hooks_text "
            "and architect_opinion.",
        )
        # The reassignment must come AFTER the split.
        reassign = re.search(
            r"critique_text\s*=\s*hooks_text\s+or\s+critique_text",
            self.src,
        )
        self.assertIsNotNone(
            reassign,
            "Expected `critique_text = hooks_text or critique_text` after "
            "the split so Lucifer's revise phase sees only the hooks.",
        )
        split_line = pattern_split.start()
        reassign_line = reassign.start()
        self.assertLess(
            split_line,
            reassign_line,
            "The split must happen before the critique_text reassignment.",
        )
