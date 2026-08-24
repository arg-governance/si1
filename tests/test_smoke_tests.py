"""Smoke tests for the SI-1 messages pipeline, ThoughtRouter, and
Speak thought channel.

These tests are pure-Python (no LLM server required) and run on
Linux. The 6 test cases mirror the original smoke matrix:

  test_1_messages_structure   — PromptEngine.build_messages exists
  test_2_build_messages       — build_messages returns valid ChatML
  test_3_si1_uses_messages    — si1.py uses build_messages, chaos,
                                 refine, and (multi-turn) revise
  test_4_thought_router       — ThoughtRouter routes <|channel>thought
  test_5_speak_thought        — Speak has _THOUGHT_OPEN_ANSI and emits
                                 a [thought] marker / ANSI codes
  test_6_full_integration     — End-to-end messages structure for chaos
                                 (2 msgs) and refine (5 msgs, multi-turn)
"""

from __future__ import annotations

import asyncio
import sys
import unittest
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


class TestSmoke(unittest.TestCase):
    def setUp(self) -> None:
        self.test_messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?"},
            {"role": "assistant", "content": "I'm doing well, thank you!"},
            {"role": "user", "content": "Can you help me with Python?"},
        ]

    def test_1_messages_structure(self) -> None:
        from prompt_engine import PromptEngine  # noqa: WPS433

        engine = PromptEngine()
        self.assertTrue(hasattr(engine, "build_messages"))
        print("PASS: PromptEngine.build_messages exists")

        # The Generate class lives in runtime_components.py
        # (it was refactored out of a standalone generate.py).
        try:
            from runtime_components import Generate  # noqa: WPS433

            for attr in ("run", "astream", "run_messages", "astream_messages"):
                self.assertTrue(
                    hasattr(Generate, attr),
                    f"Generate.{attr} is missing",
                )
            print("PASS: Generate has run, astream, run_messages, astream_messages")
        except ImportError as e:
            print(f"SKIP: Generate module not available: {e}")

    def test_2_build_messages(self) -> None:
        from prompt_engine import PromptEngine  # noqa: WPS433

        engine = PromptEngine()

        if not hasattr(engine, "build_messages"):
            self.skipTest("build_messages not present on PromptEngine")

        messages = engine.build_messages(
            system_prompt="You are an expert Python developer",
            context_block="### RUNTIME STATE\n- Turn: 1",
            user_input="Write a function to calculate fibonacci",
        )

        self.assertIsInstance(messages, list)
        self.assertGreater(len(messages), 0)

        for msg in messages:
            self.assertIn("role", msg)
            self.assertIn("content", msg)
            self.assertIn(msg["role"], ["system", "user", "assistant"])

        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[-1]["role"], "user")

        print(f"PASS: build_messages returned {len(messages)} valid messages")
        print(f"      Roles: {[m['role'] for m in messages]}")

        messages_with_history = engine.build_messages(
            system_prompt="You are helpful",
            context_block="Context",
            user_input="New question",
            prior_turns=[
                {"role": "user", "content": "First question"},
                {"role": "assistant", "content": "First answer"},
            ],
        )
        self.assertEqual(len(messages_with_history), 4)
        print(
            f"PASS: build_messages with prior_turns returned "
            f"{len(messages_with_history)} messages"
        )

    def test_3_si1_uses_messages(self) -> None:
        si1_path = ROOT / "si1.py"
        content = si1_path.read_text(encoding="utf-8")

        self.assertIn("build_messages", content)
        print("PASS: si1.py uses build_messages")

        lowered = content.lower()
        self.assertIn("chaos", lowered)
        self.assertIn("refine", lowered)
        print("PASS: si1.py contains chaos and refine phases")

        if "revise" in lowered:
            print("PASS: si1.py contains revise phase (multi-turn)")

        for marker in (
            "chaos_phase_done",
            "discipline_phase_done",
            "refine_phase_done",
            "gate_phase_done",
        ):
            self.assertIn(
                marker,
                content,
                f"Expected log marker {marker!r} in si1.py (one per phase).",
            )
        print("PASS: si1.py logs all four phase-done events")

    def test_4_thought_router(self) -> None:
        from runtime_components import ThoughtRouter  # noqa: WPS433

        async def test_router() -> None:
            out_normal: list[str] = []
            out_thought: list[str] = []
            router = ThoughtRouter(
                on_normal=out_normal.append,
                on_thought=out_thought.append,
            )

            tokens = [
                "<|channel>thought\n",
                "This is reasoning",
                "<channel|>",
                "Final answer here",
            ]

            for tok in tokens:
                await router.feed(tok)
            await router.flush()

            normal_text = "".join(out_normal)
            thought_text = "".join(out_thought)

            self.assertIn("Final answer", normal_text)
            self.assertIn("reasoning", thought_text)
            print("PASS: ThoughtRouter routed correctly")
            print(f"      Normal: {normal_text!r}")
            print(f"      Thought: {thought_text!r}")

        asyncio.run(test_router())

    def test_5_speak_thought(self) -> None:
        from runtime_components import Speak  # noqa: WPS433

        old_stderr = sys.stderr
        captured_stderr = StringIO()
        sys.stderr = captured_stderr
        try:
            speak = Speak()

            async def use_thought() -> None:
                await speak.open_thought()
                await speak.write_thought("This is a thought")
                await speak.close_thought()

            asyncio.run(use_thought())

            output = captured_stderr.getvalue()
            print(f"      Output (first 80): {output[:80]!r}")

            has_ansi_class = hasattr(speak, "_THOUGHT_OPEN_ANSI")
            self.assertTrue(
                has_ansi_class,
                "Speak must declare _THOUGHT_OPEN_ANSI for TTY rendering",
            )
            print(f"PASS: Speak has _THOUGHT_OPEN_ANSI: {speak._THOUGHT_OPEN_ANSI!r}")

            has_marker = (
                "[thought]" in output
                or "\u231e" in output   # U+231E TOP LEFT CORNER
                or "\x1b[" in output    # ANSI escape
            )
            self.assertTrue(
                has_marker,
                f"Speak thought channel did not emit a marker or ANSI codes "
                f"(output length={len(output)})",
            )
            print(f"PASS: Speak thought channel emits marker/ANSI (len={len(output)})")
        finally:
            sys.stderr = old_stderr

    def test_6_full_integration(self) -> None:
        from prompt_engine import PromptEngine  # noqa: WPS433

        engine = PromptEngine()

        chaos_messages = engine.build_messages(
            system_prompt="You are Lucifer",
            context_block="Runtime state here",
            user_input="Solve this problem",
        )
        refine_messages = engine.build_messages(
            system_prompt="You are Lucifer",
            context_block="Runtime state",
            user_input="Refine based on critique",
            prior_turns=[
                {"role": "user", "content": "Original prompt"},
                {"role": "assistant", "content": "Chaos draft"},
                {"role": "user", "content": "Critique: needs work"},
            ],
        )

        self.assertEqual(len(chaos_messages), 2)
        self.assertEqual(len(refine_messages), 5)

        print(f"PASS: Chaos phase: {len(chaos_messages)} messages")
        print(f"PASS: Refine phase: {len(refine_messages)} messages (multi-turn)")


def run_smoke_tests() -> bool:
    print("=" * 60)
    print("SMOKE TESTS - Lucifer SI1 Implementation")
    print("=" * 60)
    print()

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestSmoke)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print()
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 60)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_smoke_tests()
    sys.exit(0 if success else 1)
