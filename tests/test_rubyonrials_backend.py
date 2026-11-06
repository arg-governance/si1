from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "rubyonrials"))

import backend  # noqa: E402


class _AsyncContext:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None


class _FakeSpeaker:
    def __init__(self) -> None:
        self.stream = sys.stdout

    async def run(self, text: str) -> None:
        self.stream.write(f"[box] {text}\n")


class _FakeRuntime:
    def __init__(self) -> None:
        self.listener = object()
        self.original_listener = self.listener
        self.speaker = _FakeSpeaker()
        self.original_stream = self.speaker.stream
        self.lucifer = _AsyncContext()
        self.obi = SimpleNamespace(generate=_AsyncContext())
        self.runtime = SimpleNamespace(last_output="", turn=0)
        self.seen_prompt = ""

    async def run_iteration(self) -> None:
        self.seen_prompt = await self.listener.run()
        await self.speaker.run("boxed phase output")
        self.runtime.turn += 1
        self.runtime.last_output = "final answer"


class TestRailsPythonBackend(unittest.TestCase):
    def test_health_and_request_validation(self) -> None:
        client = backend.app.test_client()
        self.assertEqual(client.get("/health").status_code, 200)
        self.assertEqual(client.post("/chat", data="bad").status_code, 400)
        self.assertEqual(client.post("/chat", json={"prompt": " "}).status_code, 400)

    def test_chat_returns_final_output_and_phase_trace(self) -> None:
        runtime = _FakeRuntime()
        with patch.object(backend, "_get_runtime", return_value=runtime):
            response = backend.app.test_client().post(
                "/chat",
                json={"prompt": "hello Architect"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["response"], "final answer")
        self.assertEqual(response.json["turn"], 1)
        self.assertIn("boxed phase output", response.json["trace"])
        self.assertEqual(runtime.seen_prompt, "hello Architect")
        self.assertIs(runtime.listener, runtime.original_listener)
        self.assertIs(runtime.speaker.stream, runtime.original_stream)


if __name__ == "__main__":
    unittest.main()
