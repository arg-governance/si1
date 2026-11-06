"""Flask JSON adapter for the SI-1 Python runtime.

Run from the repository root with ``python rubyonrials/backend.py``. Rails
can proxy ``POST /chat`` to this service using ``SI1_PYTHON_BACKEND_URL``.
"""

from __future__ import annotations

import asyncio
import io
import os
import sys
import threading
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request


SI1_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("SI1_ROOT", str(SI1_ROOT))
if str(SI1_ROOT) not in sys.path:
    sys.path.insert(0, str(SI1_ROOT))

from si1 import build_runtime  # noqa: E402

app = Flask(__name__)
_runtime = None
_runtime_init_lock = threading.Lock()
_request_lock = threading.Lock()


def _get_runtime():
    global _runtime
    if _runtime is None:
        with _runtime_init_lock:
            if _runtime is None:
                _runtime = asyncio.run(build_runtime())
    return _runtime


async def _run_prompt(runtime: Any, prompt: str) -> dict[str, Any]:
    original_listener = runtime.listener
    original_stream = runtime.speaker.stream
    trace_stream = io.StringIO()

    class OneShotListener:
        async def run(self) -> str:
            return prompt

    runtime.listener = OneShotListener()
    runtime.speaker.stream = trace_stream
    try:
        async with runtime.lucifer, runtime.obi.generate:
            await runtime.run_iteration()
    finally:
        runtime.listener = original_listener
        runtime.speaker.stream = original_stream

    return {
        "response": runtime.runtime.last_output,
        "trace": trace_stream.getvalue(),
        "turn": runtime.runtime.turn,
    }


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/chat")
def chat():
    if not request.is_json:
        return jsonify({"error": "Expected JSON body"}), 400

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Expected a JSON object"}), 400

    prompt = data.get("prompt", "")
    prompt = prompt.strip() if isinstance(prompt, str) else ""
    if not prompt:
        return jsonify({"error": "Empty prompt"}), 400

    try:
        with _request_lock:
            runtime = _get_runtime()
            result = asyncio.run(_run_prompt(runtime, prompt))
    except Exception as exc:  # noqa: BLE001 - return a diagnosable API error
        app.logger.exception("SI-1 request failed")
        return jsonify({"error": str(exc)}), 500

    return jsonify(result)


if __name__ == "__main__":
    app.run(
        host=os.environ.get("SI1_BACKEND_HOST", "127.0.0.1"),
        port=int(os.environ.get("SI1_BACKEND_PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG", "0") == "1",
        use_reloader=False,
    )
