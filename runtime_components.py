from __future__ import annotations

import asyncio
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Optional

import aiohttp
from aiohttp import ClientTimeout

import config
import models as M
import memory_store


# ============================================================ result objects
@dataclass
class GenerationResult:
    text: str
    backend: str
    model: str
    elapsed_s: float
    stream: bool = False
    raw: dict[str, Any] = field(default_factory=dict)
    # Populated when the backend splits reasoning into a separate
    # field (llama.cpp's ``reasoning_format=deepseek``). Empty string
    # otherwise. Always carries the *raw* reasoning as the server
    # sent it — inline ``<|channel>thought`` tags are NOT stripped
    # here; the runtime can do that downstream if needed.
    thought_text: str = ""


@dataclass
class MemoryUpdateResult:
    added: list[M.Fact]
    removed: list[M.Fact]
    kept: list[M.Fact]


# ================================================================ Listen
class Listen:
    """Async user input. Wraps blocking input() in asyncio.to_thread."""

    def __init__(
        self,
        prompt: str = "\n> ",
        input_fn: Optional[Callable[[str], str]] = None,
    ) -> None:
        self.prompt = prompt
        self._input_fn = input_fn  # for testing

    async def run(self) -> str:
        if self._input_fn is not None:
            return await asyncio.to_thread(self._input_fn, self.prompt)
        return (await asyncio.to_thread(input, self.prompt)).strip()


# ================================================================ Generate
class Generate:
    """
    Async LLM backend dispatcher.

    - HTTP backend:  native async via aiohttp.ClientSession
    - llama_cpp:     C-bound, wrapped with asyncio.to_thread
    - Both expose:   run()    -> full completion
                     astream() -> async token iterator
    - Used as an async context manager so the aiohttp session is closed cleanly.
    """
    
    def __init__(
        self,
        backend: str = config.LLM_BACKEND,
        http_url: str = "",  # Remove the hardcoded 8080 default
        model: str = "",
        sampling: Optional[dict] = None,
        timeout_s: float = 600.0,
        chat_template_kwargs: Optional[dict] = None,
    ) -> None:
        """Async LLM backend dispatcher.

        ``timeout_s`` is the single source of truth for the HTTP deadline. It
        is applied to both the aiohttp session (covering connect+read idle
        time) and to every per-call ``timeout=`` override on the
        ``session.post(...)`` call, so the same value governs both the
        blocking ``run()`` path and the streaming ``astream()`` path.
        Default 600s matches the previous hard-coded value.

        ``chat_template_kwargs`` is forwarded to llama-server as
        ``chat_template_kwargs`` in the request body. The most
        important use is ``{"enable_thinking": true}`` for Gemma-4
        and similar models that have a reasoning channel in their
        chat template — without this, the template defaults to
        non-thinking mode and the model will not emit
        ``<|channel>thought`` blocks. The runtime does not interpret
        this dict; the server applies it to the jinja template.
        """
        if not http_url:
            raise ValueError(
                "CRITICAL ARCHITECTURAL ERROR: 'http_url' must be explicitly provided. "
                "Ensure your role configuration maps to the correct backend port (666 or 999)."
            )
        self.backend = backend
        self.http_url = http_url.rstrip("/")
        self.model = model
        self.sampling: dict = dict(sampling) if sampling is not None else {}
        self.chat_template_kwargs: dict = (
            dict(chat_template_kwargs) if chat_template_kwargs is not None else {}
        )
        self._timeout_s = float(timeout_s)
        self._session: Optional[aiohttp.ClientSession] = None

    # -------------------------------------------------------- payload
    def _build_payload(
        self, messages: list[dict[str, str]], stream: bool
    ) -> dict[str, Any]:
        """Build the ``/v1/chat/completions`` request body.

        ``chat_template_kwargs`` is forwarded only when non-empty so
        backends that don't recognise the field (older llama-server
        builds, non-Gemma templates) don't reject the request with a
        400. The Gemma-4 template uses ``enable_thinking`` to decide
        whether to emit the leading ``<|think|>`` token, so passing
        ``{"enable_thinking": True}`` here lets us drop the
        ``--reasoning on`` server flag and toggle thinking per
        request instead.
        """
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            **self.sampling,
        }
        if self.chat_template_kwargs:
            payload["chat_template_kwargs"] = self.chat_template_kwargs
        return payload

    # -------------------------------------------------------- session mgmt
    async def __aenter__(self) -> "Generate":
        if self.backend == "legacy_http":
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._timeout_s)
            )
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None

    # ---------------------------------------------------------- full call
    async def run(self, prompt: str) -> GenerationResult:
        if self.backend == "legacy_http":
            return await self._run_http(prompt)
        raise ValueError(f"Unknown LLM backend: {self.backend}")

    # --------------------------------------------------------- full call (messages)
    async def run_messages(
        self, messages: list[dict[str, str]]
    ) -> GenerationResult:
        """Full-completion variant that passes a real ChatML ``messages`` list.

        Use this when the caller wants the model to receive a proper
        multi-turn conversation with ``system``/``user``/``assistant``
        roles. ``llama-server`` applies the model's chat template
        (Gemma-4's ``<|turn>role\\n...<turn|>`` tokens, etc.) to the
        messages list, so the model sees system instructions as a
        system role and prior turns as their own roles.

        ``messages`` is a list of ``{"role": ..., "content": ...}``
        dicts. The ``content`` field is the plain string content.
        """
        if self.backend == "legacy_http":
            return await self._run_http_messages(messages)
        raise ValueError(f"Unknown LLM backend: {self.backend}")

    # --------------------------------------------------------- streaming
    async def astream(
        self,
        prompt: str,
        on_token: Optional[Callable[[str], None]] = None,
        on_thought_token: Optional[Callable[[str], None]] = None,
        on_parse_error: Optional[Callable[[str], None]] = None,
    ) -> "AsyncTokenStream":
        """Returns an async token iterator. Iterate with `async for`.

        ``on_token`` is fired for every *content* token (use for
        typewriter-style streaming output). ``on_thought_token`` is
        fired for every *reasoning* token when the server splits
        thoughts into a separate field (``reasoning_content``). For
        backends that don't, leave it as ``None`` and the
        :class:`ThoughtRouter` downstream can still extract thoughts
        from inline ``<|channel>thought`` markers.

        ``on_parse_error`` is invoked with the raw ``data:`` payload
        whenever the SSE chunk is malformed, so a ``stream_parse_error``
        duel-log entry can be emitted instead of silently dropping the
        chunk.
        """
        if self.backend == "legacy_http":
            inner = self._astream_http(prompt, on_parse_error=on_parse_error)
        else:
            raise ValueError(f"Unknown LLM backend: {self.backend}")
        return AsyncTokenStream(
            inner, self.backend, self.model,
            on_token=on_token, on_thought_token=on_thought_token,
        )

    # ----------------------------------------------------- streaming (messages)
    async def astream_messages(
        self,
        messages: list[dict[str, str]],
        on_token: Optional[Callable[[str], None]] = None,
        on_thought_token: Optional[Callable[[str], None]] = None,
        on_parse_error: Optional[Callable[[str], None]] = None,
    ) -> "AsyncTokenStream":
        """Streaming variant that passes a real ChatML ``messages`` list.

        See :meth:`run_messages` for the rationale. ``on_token`` and
        ``on_thought_token`` and ``on_parse_error`` are the same
        callbacks as :meth:`astream`.
        """
        if self.backend == "legacy_http":
            inner = self._astream_http_messages(
                messages, on_parse_error=on_parse_error,
            )
        else:
            raise ValueError(f"Unknown LLM backend: {self.backend}")
        return AsyncTokenStream(
            inner, self.backend, self.model,
            on_token=on_token, on_thought_token=on_thought_token,
        )

    # --------------------------------------------------- HTTP (aiohttp)
    async def _run_http(self, prompt: str) -> GenerationResult:
        # Legacy single-user-message path. Kept for callers that haven't
        # migrated to ``_run_http_messages`` yet; will be removed once
        # all four-phase call sites are on the messages pipeline.
        return await self._run_http_messages(
            [{"role": "user", "content": prompt}]
        )

    async def _run_http_messages(
        self, messages: list[dict[str, str]]
    ) -> GenerationResult:
        assert self._session is not None, "Generate must be used as async context manager"
        url = f"{self.http_url}/v1/chat/completions"
        payload = self._build_payload(messages, stream=False)
        t0 = time.time()
        # Same deadline the session was opened with. Keeps the
        # constructor-level ``timeout_s`` the single source of truth and
        # avoids duplicating magic numbers across call sites.
        custom_timeout = ClientTimeout(total=self._timeout_s)

        async with self._session.post(url, json=payload, timeout=custom_timeout) as resp:
            resp.raise_for_status()
            data = await resp.json()
        text = data["choices"][0]["message"]["content"]
        return GenerationResult(
            text=text,
            backend="http",
            model=self.model,
            elapsed_s=time.time() - t0,
            stream=False,
            raw=data,
        )

    async def _astream_http(
        self,
        prompt: str,
        on_parse_error: Optional[Callable[[str], None]] = None,
    ) -> AsyncIterator[str]:
        # Legacy single-user-message streaming path. Delegates to the
        # messages variant so there is exactly one SSE consumer in the
        # file. Kept for callers that haven't migrated yet.
        async for tok in self._astream_http_messages(
            [{"role": "user", "content": prompt}],
            on_parse_error=on_parse_error,
        ):
            yield tok

    async def _astream_http_messages(
        self,
        messages: list[dict[str, str]],
        on_parse_error: Optional[Callable[[str], None]] = None,
    ) -> AsyncIterator[str]:
        """Streaming ``/v1/chat/completions`` consumer.

        ``on_parse_error`` is an optional callback invoked with the raw
        ``data:`` payload whenever ``json.loads`` fails or the line has an
        unexpected shape. The default behaviour is a silent ``continue``;
        passing a callback lets the caller surface a ``stream_parse_error``
        duel-log entry without coupling this module to the logger.
        """
        assert self._session is not None, "Generate must be used as async context manager"
        url = f"{self.http_url}/v1/chat/completions"
        payload = self._build_payload(messages, stream=True)
        # Streaming is the path that most needs a deadline: a hung socket
        # will not surface until the session's ``total`` fires. Pass the
        # same per-call override as ``_run_http`` for consistency.
        custom_timeout = ClientTimeout(total=self._timeout_s)
        async with self._session.post(url, json=payload, timeout=custom_timeout) as resp:
            resp.raise_for_status()
            async for raw_line in resp.content:
                line = raw_line.decode("utf-8", errors="ignore").strip()
                if not line or not line.startswith("data:"):
                    continue
                chunk = line[len("data:"):].strip()
                if chunk == "[DONE]":
                    break
                try:
                    obj = json.loads(chunk)
                    choice = obj["choices"][0]
                    delta = choice.get("delta") or {}
                    # ``reasoning_content`` is the llama.cpp
                    # ``reasoning_format=deepseek`` field (per
                    # ``tools/server/README.md``): thoughts are split
                    # from the answer into a separate JSON field. The
                    # model still emits inline ``<|channel>thought``
                    # tags inside ``content`` too — those are stripped
                    # by the downstream :class:`ThoughtRouter` so the
                    # answer channel stays clean.
                    #
                    # We yield a tagged tuple ``(channel, text)`` so
                    # the caller's ``on_token`` callback can route
                    # thoughts vs. content without re-parsing the
                    # token. ``AsyncTokenStream`` only knows how to
                    # forward strings, so we collapse back to a string
                    # in :meth:`astream_messages` below.
                    rc = delta.get("reasoning_content")
                    if rc:
                        yield ("reasoning", rc)
                    ct = delta.get("content")
                    if ct:
                        yield ("content", ct)
                except (json.JSONDecodeError, KeyError, IndexError, TypeError):
                    if on_parse_error is not None:
                        on_parse_error(chunk)
                    continue



# ====================================================== ThoughtRouter
# Gemma-4 (and similar QAT/MTP reasoning models) emit internal
# ``<|channel>thought\\n...\\n<channel|>`` blocks during generation when
# ``enable_thinking`` is set on the chat template. The runtime needs to
# separate this reasoning from the actual answer so the Architect sees
# two visually distinct streams (dim/italic thought vs. normal answer)
# and so the duellog stores the cleaned answer without the reasoning
# block polluting the parseable text.
#
# ``ThoughtRouter`` is a small per-stream state machine. Feed it raw
# tokens as they arrive from the backend; it routes each token to one
# of two writers (``on_thought`` or ``on_normal``) based on which
# channel is currently open. The wrapper tags themselves (``<|channel>``,
# ``thought``, ``<channel|>``) are NOT passed to either writer.
#
# Both ``<|channel>thought`` (Gemma-4 native) and the legacy
# ``<think>...</think>`` / ``<reasoning>...</reasoning>`` / 
# ``[THOUGHT]...[/THOUGHT]`` pairs are recognized so older prompt
# formats keep working without code changes. The router is a *stream
# filter*, not a parser — it does not validate the rest of the model's
# output.
class ThoughtRouter:
    """Routes streamed tokens to ``on_thought`` / ``on_normal`` writers.

    Usage::

        router = ThoughtRouter(
            on_thought=partial(speaker.write, channel="thought"),
            on_normal=partial(speaker.write, channel="normal"),
        )
        async for token in stream:
            await router.feed(token)
        cleaned = router.normal_text  # the final answer without tags

    The two callbacks are awaited when they are coroutines and called
    inline when they are plain callables, matching the contract used by
    ``AsyncTokenStream``'s ``on_token``.
    """

    # Order matters: longer / more specific prefixes first so we don't
    # partially match. ``<|channel|>`` is the closer; ``<|channel>`` is
    # the opener prefix (channel name follows).
    _OPENS: tuple[str, ...] = (
        "<|channel>thought",  # Gemma-4 native (per jinja-gemma4 template)
        "<reasoning>",
        "<think>",
        "[THOUGHT]",
    )
    _CLOSES: tuple[str, ...] = (
        "<channel|>",          # Gemma-4 closer
        "</reasoning>",
        "</think>",
        "[/THOUGHT]",
    )

    def __init__(
        self,
        on_thought: Optional[Callable[[str], Any]] = None,
        on_normal: Optional[Callable[[str], Any]] = None,
    ) -> None:
        self._on_thought = on_thought
        self._on_normal = on_normal
        self._in_thought = False
        self._buffer = ""  # accumulates partial tags across tokens
        self.normal_text = ""
        self.thought_text = ""

    @property
    def in_thought(self) -> bool:
        return self._in_thought

    async def feed(self, token: str) -> None:
        if not token:
            return
        # Append the new token to the rolling buffer, then scan the
        # whole buffer for the longest matching open/close tag. Tokens
        # that fall outside any tag are routed normally; tokens that
        # fall inside the matched span are routed to the thought
        # channel. Anything left in the buffer after a flush is carried
        # over to the next token.
        self._buffer += token
        await self._flush_buffer()

    async def flush(self) -> None:
        """Drain any remaining buffered text. Call after the stream ends."""
        if self._buffer:
            await self._emit(self._buffer)
            self._buffer = ""

    async def _flush_buffer(self) -> None:
        # Repeatedly scan for tags until no more complete tag is in the
        # buffer. This is O(n) per scan and the buffer is small (a few
        # tokens worth), so the total cost is linear in the stream.
        while self._buffer:
            tag, kind = self._find_tag(self._buffer)
            if tag is None:
                # No complete tag visible. If the buffer could be the
                # start of a tag, hold it back; otherwise emit the
                # safe-to-emit prefix.
                hold = self._tag_prefix_len(self._buffer)
                if hold == len(self._buffer):
                    return  # whole buffer could be a tag — wait
                emit, self._buffer = self._buffer[:-hold], self._buffer[-hold:]
                if emit:
                    await self._emit(emit)
                return
            # Found a complete tag.
            idx = self._buffer.find(tag)
            before = self._buffer[:idx]
            self._buffer = self._buffer[idx + len(tag):]
            if before:
                await self._emit(before)
            if kind == "open":
                self._in_thought = True
            else:  # close
                self._in_thought = False

    async def _emit(self, text: str) -> None:
        cb = self._on_thought if self._in_thought else self._on_normal
        if self._in_thought:
            self.thought_text += text
        else:
            self.normal_text += text
        if cb is None:
            return
        result = cb(text)
        if asyncio.iscoroutine(result):
            await result

    @classmethod
    def _find_tag(cls, text: str) -> tuple[Optional[str], Optional[str]]:
        """Return the earliest (tag, kind) pair in ``text``, or (None, None).

        ``kind`` is ``"open"`` for an opener and ``"close"`` for a
        closer. Earlier tags win; ties broken by length (longer first)
        so we never split a multi-character opener like
        ``<|channel>thought``.
        """
        best_idx = len(text)
        best_tag: Optional[str] = None
        best_kind: Optional[str] = None
        for tag in cls._OPENS:
            i = text.find(tag)
            if 0 <= i < best_idx:
                best_idx, best_tag, best_kind = i, tag, "open"
        for tag in cls._CLOSES:
            i = text.find(tag)
            if 0 <= i < best_idx:
                best_idx, best_tag, best_kind = i, tag, "close"
            elif i == best_idx and best_kind == "open":
                # Same offset, prefer close (rare) — keep open either way.
                pass
        return best_tag, best_kind

    @staticmethod
    def _tag_prefix_len(text: str) -> int:
        """How many trailing characters of ``text`` might be the start
        of a recognized tag. If 0, the whole buffer is safe to emit.
        Otherwise the last ``hold`` characters must be held back until
        the next token (or end-of-stream) so we don't split a tag.
        """
        all_starts = (
            "<|channel>thought",
            "<|channel>",
            "<channel|>",
            "<reasoning>", "</reasoning>",
            "<think>", "</think>",
            "[THOUGHT]", "[/THOUGHT]",
        )
        max_hold = 0
        for start in all_starts:
            # Match against every suffix of ``text``.
            for n in range(1, min(len(start), len(text)) + 1):
                if text[-n:] == start[:n]:
                    if n > max_hold:
                        max_hold = n
        return max_hold


# ====================================================== AsyncTokenStream
class AsyncTokenStream:
    """Stable async-iterator wrapper over backend-specific streams.

    ``on_token`` is an optional per-token callback for the visible
    (content) channel. It is invoked *before* the token is appended to
    ``self.text``, so the consumer (e.g. a typewriter-style printer)
    sees the same token the iterator returns. The callback may be
    sync ``(str) -> None`` or async ``async def (str) -> None``;
    both signatures are auto-detected.

    ``on_thought_token`` is the same shape of callback but receives
    tokens from the model's reasoning channel (llama.cpp's
    ``reasoning_format=deepseek`` splits thoughts into
    ``delta.reasoning_content``). It is only used when the underlying
    backend yields channel-tagged tuples (the runtime's HTTP SSE
    consumer does this when the server sends ``reasoning_content``).
    For backends that don't, leave it as ``None`` and the
    :class:`ThoughtRouter` downstream can still extract thoughts from
    inline ``<|channel>thought`` markers.

    Tokens are accumulated separately: ``self.text`` is the visible
    channel (what the Architect reads), ``self.thought_text`` is the
    reasoning channel (audit-only). ``finalize()`` returns both via
    :class:`GenerationResult` extended with a ``thought_text`` field.
    """

    def __init__(
        self,
        agen: AsyncIterator[Any],
        backend: str,
        model: str,
        on_token: Optional[Callable[[str], Any]] = None,
        on_thought_token: Optional[Callable[[str], Any]] = None,
    ) -> None:
        self._agen = agen
        self.backend = backend
        self.model = model
        self._on_token = on_token
        self._on_thought_token = on_thought_token
        self._t0 = time.time()
        self.text = ""
        self.thought_text = ""

    def __aiter__(self) -> "AsyncTokenStream":
        return self

    async def __anext__(self) -> str:
        item = await self._agen.__anext__()
        # Backend can yield either a bare string (legacy path) or a
        # ``(channel, text)`` tuple (HTTP SSE with reasoning_content).
        # Detect by shape; the string path is the simple default.
        if isinstance(item, tuple) and len(item) == 2:
            channel, token = item
        else:
            channel, token = "content", item
        if not token:
            # Empty token — return as-is, don't fan out to callbacks.
            return token
        if channel == "reasoning":
            self.thought_text += token
            if self._on_thought_token is not None:
                result = self._on_thought_token(token)
                if asyncio.iscoroutine(result):
                    await result
            # Reasoning tokens are not visible — return empty so the
            # caller's ``async for token in stream: tokens.append(token)``
            # loop collects only the answer.
            return ""
        # channel == "content" (or any unknown channel → treat as content)
        if self._on_token is not None:
            result = self._on_token(token)
            if asyncio.iscoroutine(result):
                # Await (not ensure_future) so the callback completes
                # before the next token is fetched. This preserves
                # arrival order for typewriter-style output and means a
                # slow callback back-pressures the stream (the desired
                # behaviour for I/O-bound sinks like ``Speak.write``).
                await result
        self.text += token
        return token

    def finalize(self) -> GenerationResult:
        return GenerationResult(
            text=self.text,
            backend=self.backend,
            model=self.model,
            elapsed_s=time.time() - self._t0,
            stream=True,
            thought_text=self.thought_text,
        )


# ============================================================ ObserverV2
class ObserverV2:
    """Constitutional observer (Obi) for the four-phase duel loop.

    Second-generation observer design (V2). V1 was a JSON-output validator;
    V2 is a sibling-mentor who produces free-form reasoning and a strict
    single-line gate verdict.

    Two methods, two phases:
      - critique() — Discipline Phase. Free-form four-hook critique.
      - gate()     — Final Peripheral Gate. Single-line ACCEPTED/REJECT.
    System prompt loaded from config.OBI_SYSTEM_PROMPT_FILE.
    """

    def __init__(
        self,
        generate: Generate,
        system_prompt_path: Path | None = None,
        observer_system_prompt_path: Path | None = None,
    ) -> None:
        self.generate = generate
        # Obi loads BOTH prompts: the runtime identity (system.md) and his
        # own constitutional role (observer_system.md). The runtime identity
        # comes first so Obi knows which runtime he is observing, then his
        # own role prompt defines how he should behave.
        runtime_path = Path(system_prompt_path or config.SYSTEM_PROMPT_FILE)
        observer_path = Path(
            observer_system_prompt_path or config.OBI_SYSTEM_PROMPT_FILE
        )
        runtime_identity = (
            runtime_path.read_text(encoding="utf-8")
            if runtime_path.exists()
            else ""
        )
        observer_role = (
            observer_path.read_text(encoding="utf-8")
            if observer_path.exists()
            else ""
        )
        self.system_prompt = (
            f"{runtime_identity}\n\n{observer_role}".strip()
        )

    async def critique(self, original_prompt: str, draft: str) -> str:
        """Discipline Phase. Returns Obi's four-hook critique as free-form text."""
        msg = (
            f"{self.system_prompt}\n\n"
            f"--- ORIGINAL PROMPT ---\n{original_prompt}\n\n"
            f"--- LUCIFER'S DRAFT (THE CHAOS-PHASE OUTPUT) ---\n{draft}\n"
        )
        result = await self.generate.run(msg)
        return result.text

    async def critique_stream(
        self,
        original_prompt: str,
        draft: str,
        on_token,
    ) -> str:
        """Streaming variant of :meth:`critique` for typewriter display.

        ``on_token(token: str)`` is fired per-token as it arrives. The
        full text is also collected and returned so the caller can log
        it to the duellog exactly as in the non-streaming path.
        """
        msg = (
            f"{self.system_prompt}\n\n"
            f"--- ORIGINAL PROMPT ---\n{original_prompt}\n\n"
            f"--- LUCIFER'S DRAFT (THE CHAOS-PHASE OUTPUT) ---\n{draft}\n"
        )
        tokens: list[str] = []
        stream = await self.generate.astream(msg)
        async for token in stream:
            tokens.append(token)
            if on_token is not None:
                result = on_token(token)
                if asyncio.iscoroutine(result):
                    await result
        return "".join(tokens)

    async def gate(
        self,
        revised_text: str,
        last_critique: str,
    ) -> tuple[M.DuelVerdict, M.GatePayload | None]:
        """Final Peripheral Gate. Returns (verdict, payload) where payload is
        Lucifer's per-hook engagement bits parsed from the line after
        ``[ALIGNED]:``, or None if the draft did not include a valid payload.

        Substantively-addressed rule: each ``accepted`` bit must be backed
        by a noun phrase from the corresponding hook in the body of the
        revised draft; each ``disagreed`` bit must be backed by a sentence
        beginning ``I disagree with hook N because …``. The runtime checks
        this itself; Obi's job is to read the bit and judge honesty. The
        gate verdict remains a single ``ACCEPTED`` / ``REJECT`` line.
        """
        msg = (
            f"{self.system_prompt}\n\n"
            f"--- OBI'S LAST CRITIQUE (DISCIPLINE-PHASE OUTPUT) ---\n{last_critique}\n\n"
            f"--- LUCIFER'S REVISED DRAFT ---\n{revised_text}\n\n"
            f"Decide: is the [ALIGNED]: token present, is the four-bit "
            f"payload on the next line (`accepted` or `disagreed` per hook), "
            f"and is each bit honestly honored in the body? Reply with EXACTLY "
            f"one line: 'ACCEPTED' or 'REJECT' on the first line, and if REJECT, "
            f"a single 'reason: ...' line beneath it. Nothing else."
        )
        result = await self.generate.run(msg)
        verdict = M.DuelVerdict.from_gate_text(result.text)
        _, payload, _ = M.find_aligned_payload(revised_text)
        return verdict, payload

    async def gate_stream(
        self,
        revised_text: str,
        last_critique: str,
        on_token,
    ) -> tuple[M.DuelVerdict, M.GatePayload | None]:
        """Streaming variant of :meth:`gate` for typewriter display.

        Returns the parsed verdict + payload. ``on_token`` fires per
        token as Obi emits the verdict line(s). Note: with the gate's
        ``max_tokens=32`` and ``temperature=0.0`` the stream is usually
        a single short line; streaming is kept for consistency with
        critique and to give the Architect real-time feedback.
        """
        msg = (
            f"{self.system_prompt}\n\n"
            f"--- OBI'S LAST CRITIQUE (DISCIPLINE-PHASE OUTPUT) ---\n{last_critique}\n\n"
            f"--- LUCIFER'S REVISED DRAFT ---\n{revised_text}\n\n"
            f"Decide: is the [ALIGNED]: token present, is the four-bit "
            f"payload on the next line (`accepted` or `disagreed` per hook), "
            f"and is each bit honestly honored in the body? Reply with EXACTLY "
            f"one line: 'ACCEPTED' or 'REJECT' on the first line, and if REJECT, "
            f"a single 'reason: ...' line beneath it. Nothing else."
        )
        tokens: list[str] = []
        stream = await self.generate.astream(msg)
        async for token in stream:
            tokens.append(token)
            if on_token is not None:
                result = on_token(token)
                if asyncio.iscoroutine(result):
                    await result
        verdict = M.DuelVerdict.from_gate_text("".join(tokens))
        _, payload, _ = M.find_aligned_payload(revised_text)
        return verdict, payload


# =============================================================== Memorize
class Memorize:
    """Async fact extraction + validation + dedup."""

    def __init__(self, generate: Generate) -> None:
        self.generate = generate

    async def update(
        self,
        existing: list[M.Fact],
        conversation: list[dict[str, str]],
    ) -> MemoryUpdateResult:
        # Local imports keep module load fast and avoid circulars
        from fact_extractor import RegexFactExtractor
        from fact_validator import FactValidator

        regex = RegexFactExtractor()
        validator = FactValidator()

        # Fast path: regex extraction from assistant text (no LLM call).
        # RegexFactExtractor.extract(user_input, model_output) takes both;
        # the assistant turn plays the role of model_output.
        candidates: list[str] = []
        for turn in conversation:
            if turn.get("role") == "assistant":
                candidates.extend(
                    regex.extract(user_input="", model_output=turn["content"])
                )

        # Optional LLM enrichment when regex returns nothing
        if not candidates:
            enrichment_prompt = (
                "Extract any durable, user-stated facts from the conversation. "
                "Return each on its own line. If none, return an empty string.\n\n"
                + "\n".join(t.get("content", "") for t in conversation)
            )
            res = await self.generate.run(enrichment_prompt)
            for line in res.text.splitlines():
                line = line.strip(" -\t")
                if line:
                    candidates.append(line)

        # Validate using FactValidator's batch signature. The result is a
        # FactValidationResult carrying facts[], rejected[], warnings[].
        validation = validator.validate(candidates, existing)
        valid: list[M.Fact] = list(validation.facts)

        # Dedup against existing (FactValidator already dedups within the
        # batch, but cross-batch dedup is still our responsibility here).
        existing_stmts = {f.statement.lower() for f in existing}
        added: list[M.Fact] = []
        for f in valid:
            if f.statement.lower() not in existing_stmts:
                added.append(f)
                existing_stmts.add(f.statement.lower())

        kept = list(existing)
        removed: list[M.Fact] = []
        return MemoryUpdateResult(added=added, removed=removed, kept=kept)


# =========================================================== ArchiveManager
class ArchiveManager:
    """Async archive with AI summarization."""

    def __init__(
        self,
        generate: Generate,
        max_sessions: int = config.MAX_ARCHIVE_SESSIONS,
    ) -> None:
        self.generate = generate
        self.max_sessions = max_sessions

    async def append(
        self,
        entry: M.ArchiveEntry,
        archive: list[M.ArchiveEntry],
    ) -> list[M.ArchiveEntry]:
        archive.append(entry)
        return self.trim(archive)

    async def summarize(
        self,
        session_id: str,
        turns: list[dict[str, str]],
    ) -> str:
        joined = "\n".join(
            f"{t.get('role','?').upper()}: {t.get('content','')}" for t in turns
        )
        prompt = (
            "Summarize the following session in <= "
            f"{config.ARCHIVE_SUMMARY_CHARS} chars, preserving key facts, "
            "decisions, and open questions.\n\n" + joined
        )
        res = await self.generate.run(prompt)
        return res.text.strip()[: config.ARCHIVE_SUMMARY_CHARS]

    def trim(self, archive: list[M.ArchiveEntry]) -> list[M.ArchiveEntry]:
        if len(archive) <= self.max_sessions:
            return archive
        return archive[-self.max_sessions:]


# ================================================================ Speak
class Speak:
    """Async print. Wraps blocking write+flush in a single to_thread call.

    Two write modes for the normal stream:

    * ``run(text)`` appends a trailing newline. Use this for whole-line
      output (final responses, log lines, fallback messages) — every
      call is a complete record on its own line.
    * ``write(text)`` does NOT append a newline. Use this for
      sub-line streaming (e.g. the chaos-phase typewriter effect) where
      many tokens share one visual line. ``flush()`` may be called
      separately to force a flush without writing anything.

    A separate *thought* stream (``open_thought`` / ``write_thought`` /
    ``close_thought``) writes to ``sys.stderr`` with ANSI dim+italic so
    Gemma-4's ``<|channel>thought`` reasoning can be visually
    separated from the actual draft. The thought stream is a single
    visual line per block, terminated by ``close_thought``.
    """

    def __init__(self, stream=None) -> None:
        # The thought stream is hard-coded to stderr; the normal
        # stream (``self.stream``) is whatever was passed in. This keeps
        # the public ``Speak(stream=...)`` override working for the
        # final answer without affecting reasoning output.
        self.stream = stream or sys.stdout
        self._thought_open = False

    async def run(self, text: str) -> None:
        def _write_flush(stream, line: str) -> None:
            # Single atomic-ish write+flush per line keeps output
            # ordered even if multiple Speak coroutines race.
            stream.write(line)
            stream.flush()

        await asyncio.to_thread(_write_flush, self.stream, text + "\n")

    async def write(self, text: str) -> None:
        """Write ``text`` to the underlying stream without appending a newline.

        Tokens streamed during the chaos phase share one visual line, so
        each token is written raw. The caller is responsible for emitting
        a terminating newline (via ``run("")`` or ``write("\\n")``) when
        the stream is done.
        """
        def _do_write(stream, payload: str) -> None:
            stream.write(payload)
            stream.flush()

        if text:
            await asyncio.to_thread(_do_write, self.stream, text)

    async def flush(self) -> None:
        """Flush the underlying stream without writing anything."""
        def _do_flush(stream) -> None:
            stream.flush()

        await asyncio.to_thread(_do_flush, self.stream)

    # ----------------------------------------------- thought channel (stderr)
    # The ``thought`` channel is a separate visual stream for the model's
    # internal reasoning (``<|channel>thought`` blocks emitted by
    # Gemma-4 in thinking mode). It writes to ``sys.stderr`` with ANSI
    # dim+italic, prefixed with a small marker so the Architect can
    # tell reasoning from final answer at a glance. Each thought block
    # is a single visual line (no embedded newlines) so the typewriter
    # effect reads as one continuous line.
    #
    # TTY detection: when ``sys.stderr`` is not a TTY (e.g. redirected
    # to a file or piped), the ANSI codes are skipped to keep the
    # captured log plain. A wrapping ``[thought]...[/thought]`` marker
    # is still emitted so non-TTY capture preserves the channel split.
    _THOUGHT_OPEN_ANSI = "\x1b[2;3m"   # dim + italic
    _THOUGHT_CLOSE_ANSI = "\x1b[0m"
    _THOUGHT_PREFIX = "  ⌞ "            # visual marker, two-space indent

    async def open_thought(self) -> None:
        """Begin a thought block. Emits a single ``[thought]`` opener line."""
        if self._thought_open:
            return
        self._thought_open = True
        prefix = "[thought]"
        await asyncio.to_thread(self._write_thought_sync, prefix + "\n")

    async def write_thought(self, text: str) -> None:
        """Append ``text`` to the currently-open thought block."""
        if not text:
            return
        await asyncio.to_thread(self._write_thought_sync, text)

    async def close_thought(self) -> None:
        """Close the currently-open thought block. Emits a closing line."""
        if not self._thought_open:
            return
        self._thought_open = False
        suffix = "[/thought]"
        await asyncio.to_thread(self._write_thought_sync, "\n" + suffix + "\n")

    def _write_thought_sync(self, text: str) -> None:
        """Single-threaded writer for the thought stream (stderr).

        Uses ANSI dim+italic when stderr is a TTY; otherwise emits the
        text verbatim. A leading ``  ⌞ `` marker (U+231E) is added
        when the block first opens so non-TTY capture shows where
        thought content begins.
        """
        s = sys.stderr
        if not text:
            return
        if s.isatty():
            if text.startswith("\n"):
                # Block transition — emit the prefix only after a newline.
                s.write(text)
            else:
                s.write(self._THOUGHT_OPEN_ANSI + text + self._THOUGHT_CLOSE_ANSI)
        else:
            s.write(text)
        s.flush()


# ================================================================ Update
class Update:
    """Async runtime state + facts + archive persistence."""

    def __init__(self, memory: memory_store.MemoryStore) -> None:
        self.memory = memory

    async def run(
        self,
        runtime: M.RuntimeState,
        facts: list[M.Fact],
        archive: list[M.ArchiveEntry],
    ) -> None:
        await self.memory.save(runtime, facts, archive)