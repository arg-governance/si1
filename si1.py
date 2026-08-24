from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiohttp

import config
import models as M
from memory_store import MemoryStore
from logger import Logger, DuelLog
from prompt_engine import PromptEngine
from runtime_components import (
    ArchiveManager,
    Generate,
    Listen,
    Memorize,
    ObserverV2,
    Speak,
    Update,
)
# ``runtime_components`` itself is also imported as a module so the
# ``ThoughtRouter`` class (used by the chaos and refine phases to
# separate Gemma-4's ``<|channel>thought`` blocks from the actual
# draft) is reachable as ``runtime_components.ThoughtRouter``. The
# names above are the runtime *instances*; the class lives on the
# module.
import runtime_components  # noqa: E402  (used for ThoughtRouter below)

# The runtime runs exactly ONE bounded adversarial round per Architect
# turn (config.MAX_DUEL_ROUNDS=1). The four phases execute once, in
# order, and the loop ends:
#   Phase 1 (Chaos):             Lucifer emits the initial unfiltered DRAFT.
#                                Obi is NOT present.
#   Phase 2 (Discipline):        Obi critiques the DRAFT with the four-hook
#                                contract. He is given the DRAFT as
#                                input; he does not generate a new draft.
#   Phase 3 (Refined Learning):  Lucifer reads the critique and emits the
#                                REVISED draft, prefixed with [ALIGNED]:.
#   Phase 4 (Final Peripheral Gate): Obi returns ACCEPTED or REJECT.
#                                On REJECT, the runtime surfaces a hard
#                                fallback; there is no second round. The
#                                Architect re-issues the prompt to retry.
# Per turn, the runtime makes at most 2 generations (chaos + refine) and
# 2 observer calls (critique + gate). The structure is therefore
# predictable: 1 turn = 1 loop = 4 phases.


class SI1Runtime:
    def __init__(
        self,
        lucifer: Generate,
        obi: ObserverV2,
        listener: Listen,
        speaker: Speak,
        memorizer: Memorize,
        updater: Update,
        archiver: ArchiveManager,
        prompt_engine: PromptEngine,
        memory: MemoryStore,
        logger: Logger,
        duel_log: DuelLog,
        runtime: M.RuntimeState,
        facts: list[M.Fact],
        archive: list[M.ArchiveEntry],
    ) -> None:
        self.lucifer = lucifer
        self.obi = obi
        self.listener = listener
        self.speaker = speaker
        self.memorizer = memorizer
        self.updater = updater
        self.archiver = archiver
        self.prompt_engine = prompt_engine
        self.memory = memory
        self.logger = logger
        self.duel_log = duel_log

        self.runtime = runtime
        self.facts = facts
        self.archive = archive

        self._history: list[dict[str, str]] = []
        self._stop = asyncio.Event()

    # ----------------------------------------------------------- main loop
    async def run(self) -> None:
        await self.logger.log(
            "runtime_start",
            version=config.RUNTIME_VERSION,
            lucifer_model=config.LUCIFER_MODEL_NAME,
            obi_model=config.OBI_MODEL_NAME,
            lucifer_url=config.LUCIFER_URL,
            obi_url=config.OBI_URL,
            backend=config.LLM_BACKEND,
            max_duel_rounds=config.MAX_DUEL_ROUNDS,
        )
        try:
            while not self._stop.is_set():
                await self.run_iteration()
        except (KeyboardInterrupt, EOFError):
            await self.logger.log("runtime_interrupted")
        finally:
            await self.logger.log("runtime_stop", turn=self.runtime.turn)

    def request_stop(self) -> None:
        self._stop.set()

    # ----------------------------------------------------- one iteration
    async def run_iteration(self) -> None:
        # 1. Listen
        user_input = await self.listener.run()
        if not user_input:
            return
        if user_input.lower() in config.EXIT_COMMANDS:
            self.request_stop()
            await self.logger.log("exit_command", input=user_input)
            return

        # 2. Build context block (pure CPU-only string assembly, no I/O).
        # NOTE: PromptEngine already loaded the system prompt at construction,
        # so we no longer re-read it on every turn.
        snapshot = M.MemorySnapshot(
            runtime=self.runtime,
            facts=self.facts,
            archive=self.archive,
        )
        context_block = self.prompt_engine.build_context_block(snapshot)

        # 3. Four-phase duel loop. Runs the four phases exactly once
        # (Chaos -> Discipline -> Refine -> Gate). Returns the final
        # accepted text or None if Obi rejected the revised draft at
        # the gate. The third tuple element is Obi's REJECT reason (or
        # a per-phase network failure description), surfaced in the
        # fallback message so the Architect doesn't have to read
        # ``duellog.json`` to learn *why* the gate refused. The fourth
        # element is ``already_streamed`` — when True, every phase has
        # been streamed to stdout already, so the final ``Speak.run``
        # below is skipped to avoid duplicating the revised text.
        proposed, accepted_round, reject_reason, already_streamed = await self._generate_with_observer(
            user_input=user_input,
            context_block=context_block,
        )
        if proposed is None:
            # Hard rejection — Obi's gate REJECT on the single round.
            # The Architect can bypass by re-issuing the prompt with a
            # leading `[OVERRIDE]: <reason>` token. The runtime treats
            # that as a signed audit event and proceeds without
            # surfacing the constitutional-gate fallback.
            if M.find_override(user_input):
                proposed = (
                    f"[OVERRIDE acknowledged. Proceeding past the prior "
                    f"gate REJECT at the Architect's direction. Obi's "
                    f"critique is logged in duellog but not enforced for "
                    f"the prior turn. Re-state your request normally; "
                    f"the override is audit-recorded, not a permission "
                    f"slip for new content.]"
                )
                await self.logger.log("duel_overridden", turn=self.runtime.turn)
            else:
                reason_text = (
                    f" Obi said: {reject_reason}."
                    if reject_reason
                    else ""
                )
                proposed = (
                    "[Constitutional gate refused this turn. "
                    "Obi rejected the revised draft."
                    f"{reason_text} "
                    "The runtime did not pass any unaligned output to you. "
                    "To proceed past this gate, re-issue your request with "
                    "a leading `[OVERRIDE]: <reason>` token. Otherwise, "
                    "rephrase, simplify, or provide more context.]"
                )
                await self.logger.log("duel_exhausted", turn=self.runtime.turn)

        # 4. Speak (skip if the duel loop already streamed the text)
        if not already_streamed:
            await self.speaker.run(proposed)

        # 5. History
        self._history.append({"role": "user", "content": user_input})
        self._history.append({"role": "assistant", "content": proposed})

        # 6. Memorize (look at the most recent window)
        mem_result = await self.memorizer.update(self.facts, self._history[-6:])
        if mem_result.added:
            self.facts.extend(mem_result.added)
            await self.logger.log("facts_added", count=len(mem_result.added))

        # 7. Append an archive entry summarizing this turn (best-effort).
        try:
            summary = await self.archiver.summarize(
                session_id=str(self.runtime.turn),
                turns=self._history[-2:],
            )
            new_entry = M.ArchiveEntry(
                time=self._now_iso(),
                summary=summary,
            )
            self.archive = await self.archiver.append(new_entry, self.archive)
            await self.logger.log("archive_appended", turn=self.runtime.turn)
        except Exception as e:  # noqa: BLE001 - archive is best-effort
            await self.logger.log_failure("archive_failed", e)

        # 8. Update runtime state
        self.runtime.turn += 1
        self.runtime.last_active_at = self._now_iso()
        self.runtime.last_input = user_input
        self.runtime.last_output = proposed

        # 9. Persist (concurrent save via MemoryStore.save)
        await self.updater.run(self.runtime, self.facts, self.archive)

        await self.logger.log(
            "iteration_done",
            turn=self.runtime.turn,
            accepted_round=accepted_round if accepted_round is not None else -1,
        )

    # ----------------------------------------------- four-phase duel loop
    async def _generate_with_observer(
        self,
        user_input: str,
        context_block: str,
    ) -> tuple[Optional[str], Optional[int], Optional[str], bool]:
        """Run the four-phase duel loop for ONE Architect prompt.

        The loop is a single pass through four phases (config.MAX_DUEL_ROUNDS=1):
          Phase 1 — Chaos (Lucifer):            initial unfiltered DRAFT
          Phase 2 — Discipline (Obi):           four-hook critique of the DRAFT
          Phase 3 — Refined Learning (Lucifer): revise using Obi's critique,
                                                prefix the result with [ALIGNED]:
          Phase 4 — Final Peripheral Gate (Obi): ACCEPTED/REJECT verdict

        On a gate REJECT the runtime surfaces a hard-reject fallback
        immediately; there is no second round. The Architect re-issues
        the prompt if they want a retry. Per turn the runtime therefore
        makes at most 2 generations (chaos + refine) and 2 observer
        calls (critique + gate), in this exact order, then the loop ends.

        Important contract — Phase 2 input. Obi's critique is generated
        from Lucifer's DRAFT (the chaos-phase output), NOT from a new
        draft. Obi is an observer; he does not draft. The four-hook
        critique targets the draft text he is given. He must not emit
        his own [ALIGNED]: token, his own META block, or his own
        alternative answer. The runtime passes ``draft`` (the cleaned
        chaos-phase normal text) into ``ObserverV2.critique_stream``
        unchanged.

        Each phase is wrapped in its own ``try/except`` for
        ``(aiohttp.ClientError, asyncio.TimeoutError)``. A network failure
        on any single phase is logged as ``duel_phase_failed`` and the
        loop surfaces a hard reject (None, None) rather than crashing the
        runtime. Token-parse errors during chaos-phase streaming are
        logged as ``stream_parse_error`` and the chunk is dropped.

        Returns:
            (text, 0, None, True) on success. ``0`` is the (single) round
                index; the caller should NOT re-speak the returned text
                because every phase is streamed to stdout.
            (None, None, last_reject_reason, False) on hard rejection
                (gate REJECT) or on a per-phase network failure.
                ``last_reject_reason`` is Obi's reason from the gate
                (or "chaos-phase network failure: …" / etc. on a
                per-phase network error).
        """
        turn = self.runtime.turn

        # Build the real ChatML messages for the chaos phase. The system
        # prompt is sent as a proper ``system`` role (so ``llama-server``
        # applies the Gemma-4 chat template with ``<|turn>system\n``),
        # and the runtime note + kernel context + Architect's prompt
        # travel as a single user turn. We build the messages list
        # directly here (rather than via ``build_messages``) because the
        # chaos phase has a custom user-content shape — the runtime
        # note must precede the kernel context, which the standard
        # ``build_messages`` wrapper doesn't account for.
        chaos_user_content = (
            "[RUNTIME NOTE — CHAOS PHASE]\n"
            "This is the CHAOS PHASE. You are alone; Obi is not present.\n"
            "Produce an initial, unfiltered draft. Bugs, raw intuition, and\n"
            "half-formed ideas are expected and welcome. Do NOT emit the\n"
            "compliance token `[ALIGNED]:` or the 4-bit payload — those are\n"
            "for the Refined Learning Pass (Phase 3) only, after Obi has\n"
            "produced a critique. Do NOT emit a `[META]` block — that is\n"
            "for the revised draft that enters the Final Peripheral Gate.\n"
            "Just draft. Anything coherent or incoherent is acceptable here.\n"
            "\n--- ARCHITECT'S PROMPT FOLLOWS ---\n\n"
            f"KERNEL CONTEXT:\n{context_block}\n\n"
            f"USER:\n{user_input}"
        )
        chaos_messages: list[dict[str, str]] = [
            {"role": "system", "content": self.prompt_engine.system_prompt},
            {"role": "user", "content": chaos_user_content},
        ]

        # ----------------------------------------------------- Phase 1 (Chaos)
        # Tokens are streamed to stdout in typewriter style via
        # ``on_token`` AND collected into a list for O(n) ``str.join`` at
        # the end. The list-then-join pattern avoids the O(n^2) reallocation
        # cost of repeated ``draft += token`` on long drafts (a 16K-token
        # CoT draft on the Gemma-4 reasoning model would otherwise pay a
        # measurable cost on the event loop).
        #
        # Gemma-4 with MTP and ``enable_thinking`` emits
        # ``<|channel>thought\n...\n<channel|>`` blocks for internal
        # reasoning. The ThoughtRouter below detects those (and the
        # legacy ``<think>``/``<reasoning>`` pairs) and routes their
        # content to ``Speak.write_thought`` (stderr, dim/italic) while
        # the actual draft goes to stdout. The duellog stores the
        # cleaned normal text so the four-hook parser and gate don't
        # have to skip the reasoning block.
        #
        # The Lucifer session is owned by ``amain()`` (one long-lived
        # ``async with runtime.lucifer, runtime.obi.generate:``) and must
        # NOT be re-entered here. The previous version opened a new session
        # for the chaos phase and reused the closed one for the rest of
        # the loop, which only worked by accident.
        tokens: list[str] = []
        try:
            thought_router = runtime_components.ThoughtRouter(
                on_thought=self.speaker.write_thought,
                on_normal=self.speaker.write,
            )

            async def _on_parse_error(raw: str) -> None:
                await self.duel_log.record(
                    turn=turn, round=0, kind="stream_parse_error",
                    actor="runtime", text=raw[:200],
                )

            # Print a phase header so the user can see where the chaos
            # stream starts. Use ``Speak.run`` for the header line so it
            # gets its own line; ``write`` is for sub-line tokens.
            await self.speaker.run("[chaos-phase streaming Lucifer's draft…]")

            # Open the thought channel visually lazily, on the first
            # reasoning token. Per llama.cpp's Gemma-4 jinja template,
            # the reasoning channel is the first content the model emits
            # when ``enable_thinking=true``. We open it inside the first
            # on_thought_token call so we don't print an empty
            # ``[thought]`` line for outputs that have no reasoning.
            # The flag below ensures it's opened exactly once.
            thought_opened = False

            async def _on_thought_token(token: str) -> None:
                nonlocal thought_opened
                if not thought_opened:
                    await self.speaker.open_thought()
                    thought_opened = True
                await self.speaker.write_thought(token)

            stream = await self.lucifer.astream_messages(
                chaos_messages,
                on_token=thought_router.feed,
                on_thought_token=_on_thought_token,
                on_parse_error=_on_parse_error,
            )
            async for token in stream:
                if token:  # AsyncTokenStream returns "" for reasoning
                    tokens.append(token)
            # Flush the ThoughtRouter so any text that the buffer was
            # holding back (because the very last content token ended
            # with a possible tag prefix like `<` or `<|c`) is finally
            # routed to on_normal and accumulated into normal_text.
            # Without this the router's normal_text can be empty for
            # streams whose tail looks like the start of a tag, even
            # though raw_text collected via ``tokens`` has the full
            # content. Verified against the duellog: every chaos draft
            # since the chat-template change has ``text=""`` and
            # ``raw_text`` populated. This fix drains the held-back
            # buffer at end-of-stream.
            await thought_router.flush()
            # Close the visual thought channel if it was opened.
            if thought_opened:
                await self.speaker.close_thought()
            chaos_result = stream.finalize()
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            await self.duel_log.record(
                turn=turn, round=0, kind="chaos_failure", actor="runtime",
                text=f"chaos-phase network failure: {e!r}",
            )
            await self.logger.log_failure("duel_phase_failed", e, phase="chaos")
            return None, None, f"chaos-phase network failure: {e!r}", False

        # ``draft`` is the cleaned draft. The router strips any
        # inline ``<|channel>thought`` tags that may also appear in
        # the content stream (defensive — the server usually splits
        # reasoning into its own field). ``chaos_result.thought_text``
        # carries the server-side reasoning for the duellog.
        draft = thought_router.normal_text
        chaos_result_text = "".join(tokens)
        # The router has already routed; nothing more to flush.
        # Terminate the chaos stream on its own visual line. The blank
        # ``run("")`` adds ``\n`` so the next phase marker / final
        # response starts on a fresh line.
        await self.speaker.run("")
        await self.duel_log.record(
            turn=turn, round=0, kind="draft", actor="lucifer", text=draft,
            raw_text=chaos_result_text,
            thought_text=chaos_result.thought_text or thought_router.thought_text,
            elapsed_s=chaos_result.elapsed_s, model=config.LUCIFER_MODEL_NAME,
        )
        await self.logger.log(
            "chaos_phase_done",
            turn=turn, elapsed_s=chaos_result.elapsed_s, draft_len=len(draft),
        )
        # Visual rule separating phases. Using a 60-char ``===`` rule so
        # the four-phase loop reads as four distinct visual blocks in
        # the terminal: chaos / discipline / refine / gate. The rule is
        # printed before the next phase header so each phase is its own
        # boxed region.
        await self.speaker.run("")
        await self.speaker.run("=" * 60)

        # =============================================================
        # Single-pass four-phase loop. MAX_DUEL_ROUNDS is fixed at 1,
        # so the four phases below execute exactly once, in this order:
        #   Phase 2 — Discipline (Obi)            : critique the DRAFT
        #   Phase 3 — Refined Learning (Lucifer)  : revise using critique
        #   Phase 4 — Final Peripheral Gate (Obi) : ACCEPTED/REJECT
        # On a REJECT the loop surfaces a hard-reject fallback; the
        # Architect re-issues the prompt to retry. There is no second
        # round. The ``round_idx`` value in duellog rows is always 0.
        # =============================================================
        assert config.MAX_DUEL_ROUNDS == 1, (
            "This single-pass four-phase block assumes MAX_DUEL_ROUNDS == 1. "
            "The nested-round logic was removed; raise MAX_DUEL_ROUNDS only "
            "after re-introducing the round-iteration scaffolding below."
        )
        round_idx: int = 0
        last_reject_reason: Optional[str] = None

        # ------------------------------- Phase 2 (Discipline: Obi critique)
        # Streamed typewriter output, same as chaos phase. The
        # full text is also collected for the duellog. We open the
        # discipline section with the same 60-char ``===`` rule used
        # between phases so the Architect always sees a clear visual
        # break between Lucifer's chaos draft and Obi's critique.
        # Obi is given the cleaned DRAFT (``draft``) as the sole input
        # for his critique — he does NOT generate a new draft, only
        # the four-hook critique of the text he is shown.
        await self.speaker.run("=" * 60)
        await self.speaker.run(
            f"[discipline-phase streaming Obi's critique…]"
        )

        async def _print_critique_token(token: str) -> None:
            await self.speaker.write(token)

        try:
            critique_text = await self.obi.critique_stream(
                original_prompt=user_input,
                draft=draft,
                on_token=_print_critique_token,
            )
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            await self.duel_log.record(
                turn=turn, round=round_idx, kind="critique_failure",
                actor="runtime", text=f"critique network failure: {e!r}",
            )
            await self.logger.log_failure(
                "duel_phase_failed", e, phase="discipline", round=round_idx,
            )
            return None, None, f"discipline-phase network failure: {e!r}", False
        # Close the critique line.
        await self.speaker.run("")
        await self.duel_log.record(
            turn=turn, round=round_idx, kind="critique", actor="obi",
            text=critique_text, model=config.OBI_MODEL_NAME,
        )
        await self.logger.log(
            "discipline_phase_done",
            turn=turn, round=round_idx, critique_len=len(critique_text),
        )

        # Split Obi's critique into the four-hook portion (which Lucifer
        # sees during the Refined Learning Pass) and Obi's independent
        # read of the Architect's prompt (which the Architect sees but
        # Lucifer does NOT — it cannot drive a revision since Lucifer
        # cannot revise the Architect's prompt). The runtime streams the
        # Architect opinion visibly between the discipline and refine
        # phase markers so the Architect sees it on stdout, alongside
        # the chaos draft, Obi's hooks, the revise, and the gate.
        hooks_text, architect_opinion = M.split_architect_opinion(critique_text)
        if architect_opinion is not None:
            await self.speaker.run(
                f"[obi's view on the architect's prompt]"
            )
            for ln in architect_opinion.splitlines():
                await self.speaker.run(f"  {ln}")
            await self.speaker.run("")
            await self.duel_log.record(
                turn=turn, round=round_idx, kind="architect_opinion",
                actor="obi", text=architect_opinion,
                model=config.OBI_MODEL_NAME,
            )
        # Whatever Obi said, Lucifer's revise input is the hooks only.
        critique_text = hooks_text or critique_text

        await self.speaker.run("=" * 60)

        # --------------------- Phase 3 (Refined Learning: Lucifer revise)
        # Streamed like chaos. The revise phase uses a real ChatML
        # multi-turn conversation so Gemma-4 sees the chaos draft as
        # an ``assistant`` turn and Obi's critique as a follow-up
        # ``user`` turn — proper assistant→user→assistant dialogue
        # rather than a single user blob. The DRAFT (Lucifer's own
        # chaos-phase output) is the conversation history, NOT a new
        # draft; the revise phase produces the REVISED text only.
        await self.speaker.run(
            f"[refine-phase streaming Lucifer's revision…]"
        )
        revise_user_text = (
            f"--- OBI'S CRITIQUE (DISCIPLINE-PHASE OUTPUT) ---\n"
            f"{critique_text}\n\n"
            f"Revise your previous draft to address Obi's critique. "
            f"You MUST prefix your final text with the literal token "
            f"{config.ALIGNED_TOKEN} on its own line. Without that "
            f"token, the output cannot pass the gate."
        )
        revise_messages = self.prompt_engine.build_messages(
            system_prompt="",
            context_block=context_block,
            user_input=revise_user_text,
            prior_turns=[
                # The chaos DRAFT (cleaned normal text) is the assistant
                # turn the model revises. It is NOT regenerated here;
                # this phase produces only the REVISED text.
                {"role": "assistant", "content": draft},
            ],
        )
        refine_tokens: list[str] = []
        try:
            async def _on_refine_parse_error(raw: str) -> None:
                await self.duel_log.record(
                    turn=turn, round=round_idx,
                    kind="stream_parse_error", actor="runtime",
                    text=raw[:200],
                )

            refine_router = runtime_components.ThoughtRouter(
                on_thought=self.speaker.write_thought,
                on_normal=self.speaker.write,
            )
            refine_thought_opened = False

            async def _on_refine_thought_token(token: str) -> None:
                nonlocal refine_thought_opened
                if not refine_thought_opened:
                    await self.speaker.open_thought()
                    refine_thought_opened = True
                await self.speaker.write_thought(token)

            refine_stream = await self.lucifer.astream_messages(
                revise_messages,
                on_token=refine_router.feed,
                on_thought_token=_on_refine_thought_token,
                on_parse_error=_on_refine_parse_error,
            )
            async for token in refine_stream:
                if token:
                    refine_tokens.append(token)
            # Flush the refine-phase ThoughtRouter so any text that
            # the buffer held back (because the last content token
            # ended with a possible tag prefix) is finally routed
            # to on_normal. Same fix as the chaos phase above.
            await refine_router.flush()
            if refine_thought_opened:
                await self.speaker.close_thought()
            mutation = refine_router.normal_text
            mutation_raw = "".join(refine_tokens)
            mutation_thought = refine_stream.thought_text
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            await self.duel_log.record(
                turn=turn, round=round_idx, kind="refine_failure",
                actor="runtime", text=f"refine network failure: {e!r}",
            )
            await self.logger.log_failure(
                "duel_phase_failed", e, phase="refine", round=round_idx,
            )
            return None, None, f"refine-phase network failure: {e!r}", False
        # Close the refine line.
        await self.speaker.run("")
        has_token = mutation.lstrip().startswith(config.ALIGNED_TOKEN)
        await self.duel_log.record(
            turn=turn, round=round_idx, kind="mutation", actor="lucifer",
            text=mutation,
            raw_text=mutation_raw,
            thought_text=mutation_thought or refine_router.thought_text,
            has_aligned_token=has_token,
            model=config.LUCIFER_MODEL_NAME,
        )
        await self.logger.log(
            "refine_phase_done",
            turn=turn, round=round_idx,
            has_aligned_token=has_token, mutation_len=len(mutation),
        )
        await self.speaker.run("=" * 60)

        # --------------- Phase 4 (Final Peripheral Gate: Obi verdict)
        # Streamed. The gate is a short verdict line so the stream
        # is short, but it's streamed for consistency with the rest
        # of the four-phase loop.
        # Swap Obi's sampling to the deterministic gate profile just for
        # this single call, then restore the critique profile.
        original_sampling = self.obi.generate.sampling
        self.obi.generate.sampling = dict(config.OBI_SAMPLING_GATE)
        try:
            try:
                async def _print_gate_token(token: str) -> None:
                    await self.speaker.write(token)

                verdict, payload = await self.obi.gate_stream(
                    revised_text=mutation,
                    last_critique=critique_text,
                    on_token=_print_gate_token,
                )
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                await self.duel_log.record(
                    turn=turn, round=round_idx, kind="gate_failure",
                    actor="runtime", text=f"gate network failure: {e!r}",
                )
                await self.logger.log_failure(
                    "duel_phase_failed", e, phase="gate", round=round_idx,
                )
                return None, None, f"gate-phase network failure: {e!r}", False
        finally:
            self.obi.generate.sampling = original_sampling
        # Close the gate stream on its own line.
        await self.speaker.run("")

        # Runtime-side per-hook substantively-addressed check.
        # Obi's verdict is one signal; the runtime verifies the four
        # bits are actually honored in the body of the revised draft
        # (noun-phrase backing for `accepted`, "I disagree with hook N
        # because …" for `disagreed`). This makes the check parseable
        # rather than vibes-based.
        token_present, parsed_payload, body = M.find_aligned_payload(mutation)
        payload_ok = payload is not None and parsed_payload is not None
        if payload_ok:
            ok, hook_evidence = self._verify_payload_engagement(
                parsed_payload, body, critique_text,
            )
        else:
            ok, hook_evidence = False, ["no valid 4-bit payload after [ALIGNED]:"]
        payload_bits = parsed_payload.as_bits() if parsed_payload else None

        await self.duel_log.record(
            turn=turn, round=round_idx, kind="gate", actor="obi",
            text=verdict.reason if not verdict.accepted else "ACCEPTED",
            accepted=verdict.accepted, reason=verdict.reason,
            payload_bits=payload_bits,
            payload_honored=ok, hook_evidence=hook_evidence,
            model=config.OBI_MODEL_NAME,
        )
        await self.logger.log(
            "gate_phase_done",
            turn=turn, round=round_idx,
            accepted=verdict.accepted, reason=verdict.reason,
            payload_honored=ok,
        )

        # Architect-facing audit verdict. The discipline critique and
        # the revise mutation are internal-only (they live in
        # ``duellog.json`` for the auditor), but the gate verdict is
        # the audit *outcome* and the Architect needs to see it. On
        # ACCEPT we print a one-line confirmation; on REJECT we print
        # Obi's reason so the Architect knows the loop has ended.
        if verdict.accepted and ok:
            await self.speaker.run(f"[obi gate: ACCEPTED]")
        else:
            reason = verdict.reason or "no reason provided"
            await self.speaker.run(f"[obi gate: REJECT — {reason}]")

        # Record any [META] block as a separate duellog row so the
        # Architect can later reconstruct epistemic counts without
        # re-parsing free text.
        meta = M.AlignedMeta.from_text(mutation)
        if meta is not None:
            await self.duel_log.record(
                turn=turn, round=round_idx, kind="meta", actor="lucifer",
                text="", **meta.to_dict(),
            )

        # ACCEPT requires both Obi's verdict AND payload honesty.
        if verdict.accepted and ok:
            return mutation, round_idx, None, True

        # REJECT — single round, so this is a hard reject. Surface
        # Obi's reason in the duellog and the fallback message.
        last_reject_reason = verdict.reason or "no reason provided"
        await self.duel_log.record(
            turn=turn, round=round_idx, kind="rejection", actor="runtime",
            text=f"hard reject after round {round_idx}: {verdict.reason}",
            reason=verdict.reason,
        )
        return None, None, last_reject_reason, False

    # ------------------------------------------------------------- helpers
    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _extract_hook_noun_phrases(critique_text: str) -> list[list[str]]:
        """Return up to 4 lists of noun-phrase tokens extracted from each
        critique hook's body. Each hook's content is lowercased and split
        into words; stopwords are filtered out; what remains is a set of
        'content words' that should appear (or be reasonably paraphrased)
        in the revised draft if the hook was accepted.
        """
        hooks = ("you arrived at this conclusion because:",
                 "however, you overlooked:",
                 "remember our constitutional principle:",
                 "re-evaluate your reasoning:")
        result: list[list[str]] = []
        lowered = critique_text.lower()
        for hook in hooks:
            idx = lowered.find(hook)
            if idx < 0:
                result.append([])
                continue
            start = idx + len(hook)
            # Hook body ends at the next hook header or end of text.
            end = len(lowered)
            for other in hooks:
                if other == hook:
                    continue
                other_idx = lowered.find(other, start)
                if 0 <= other_idx < end:
                    end = other_idx
            body = lowered[start:end]
            tokens = [w.strip(".,;:()[]\"'`") for w in body.split()]
            # Drop very short tokens and common stopwords; keep content words.
            stopwords = {"the", "a", "an", "is", "are", "was", "were", "be",
                         "been", "being", "to", "of", "in", "on", "at", "for",
                         "with", "by", "and", "or", "but", "not", "no", "your",
                         "you", "i", "we", "they", "it", "this", "that", "as",
                         "if", "then", "so", "do", "does", "did", "have", "has",
                         "had", "from", "into", "than", "too", "very", "can",
                         "could", "would", "should", "will", "may", "might",
                         "must", "shall", "our", "their", "its", "my", "his",
                         "her", "one", "two", "any", "all", "some", "such",
                         "also", "about", "which", "what", "when", "where",
                         "why", "how", "here", "there", "now", "more", "most",
                         "other", "only", "own", "same", "so", "than", "too",
                         "very", "just", "because", "however", "principle",
                         "conclusion", "reasoning", "re-evaluate"}
            content = [t for t in tokens if len(t) >= 4 and t not in stopwords]
            result.append(content)
        return result

    @classmethod
    def _verify_payload_engagement(
        cls,
        payload: M.GatePayload,
        body: str,
        critique_text: str,
    ) -> tuple[bool, list[str]]:
        """Runtime-side substantively-addressed check.

        For each hook marked ``accepted``, at least one content word from
        the hook's body in the critique must appear in the revised draft's
        body. For each hook marked ``disagreed``, the body must contain a
        sentence beginning ``I disagree with hook N because …``.

        Returns (overall_ok, per_hook_evidence_strings).
        """
        bits = payload.as_bits()
        nouns_per_hook = cls._extract_hook_noun_phrases(critique_text)
        body_lower = body.lower()
        evidence: list[str] = []
        ok = True
        for i, (bit, nouns) in enumerate(zip(bits, nouns_per_hook), start=1):
            if bit == "disagreed":
                marker = f"i disagree with hook {i} because"
                if marker in body_lower:
                    evidence.append(f"hook{i}=disagreed+justified")
                else:
                    ok = False
                    evidence.append(f"hook{i}=disagreed but no disagree-justification")
            else:  # accepted
                if not nouns:
                    # No content words to verify against; treat as honored
                    # because we can't constructively disprove engagement.
                    evidence.append(f"hook{i}=accepted (no content-words to verify)")
                    continue
                hit = any(n in body_lower for n in nouns)
                if hit:
                    evidence.append(f"hook{i}=accepted+backed")
                else:
                    ok = False
                    evidence.append(
                        f"hook{i}=accepted but none of {nouns[:5]} appear in body"
                    )
        return ok, evidence


# ============================================================ build_runtime
async def build_runtime() -> SI1Runtime:
    """Construct a fully-wired SI-1 runtime with the two-server topology.

    Two independent ``Generate`` instances are created - one for Lucifer
    (port 666) and one for Obi (port 999). Each gets its own model identity
    and its own sampling profile from ``config``. ``ObserverV2`` is wired to
    the Obi generator; ``Memorize`` and ``ArchiveManager`` use the Lucifer
    generator (they reason about Lucifer's output, not Obi's).
    """
    memory = MemoryStore()
    logger = Logger()
    duel_log = DuelLog()
    prompt_engine = PromptEngine()

    # Lucifer (main runtime) on port 666.
    lucifer = Generate(
        http_url=config.LUCIFER_URL,
        model=config.LUCIFER_MODEL_NAME,
        sampling=config.LUCIFER_SAMPLING,
        chat_template_kwargs=config.LUCIFER_CHAT_TEMPLATE_KWARGS,
    )

    # Obi (observer) on port 999. Default sampling is the critique profile;
    # the gate() call path temporarily swaps in OBI_SAMPLING_GATE for a
    # deterministic verdict, then restores it.
    obi_gen = Generate(
        http_url=config.OBI_URL,
        model=config.OBI_MODEL_NAME,
        sampling=config.OBI_SAMPLING_CRITIQUE,
    )
    obi = ObserverV2(obi_gen)

    listener = Listen()
    speaker = Speak()
    memorizer = Memorize(lucifer)
    archiver = ArchiveManager(lucifer)
    updater = Update(memory)

    try:
        runtime, facts, archive = await memory.load()
        memory_status = "loaded"
        memory_error: str | None = None
    except Exception as e:
        print(f"[startup] could not load memory: {e}", file=sys.stderr)
        runtime = M.RuntimeState()
        facts = []
        archive = []
        memory_status = "error"
        memory_error = repr(e)

    # Log file presence check (best-effort; missing files are normal on first run)
    def _file_status(path: Path) -> str:
        try:
            if path.exists():
                size = path.stat().st_size
                return f"present ({size} bytes)"
            return "missing (will be created on first save)"
        except OSError as oe:
            return f"unreadable: {oe!r}"

    log_status = {
        "runlog": _file_status(config.RUN_LOG_FILE),
        "duellog": _file_status(config.DUEL_LOG_FILE),
    }
    memory_files = {
        "runtime": _file_status(config.RUNTIME_FILE),
        "facts": _file_status(config.FACTS_FILE),
        "archive": _file_status(config.ARCHIVE_FILE),
    }

    # Boot banner
    print("=" * 72)
    print(f"  {config.APP_NAME}")
    print(f"  {config.RUNTIME_VERSION}")
    print("-" * 72)
    print(f"  Memory: {memory_status}  "
          f"(facts={len(facts)}, archive={len(archive)}, turn={runtime.turn})")
    if memory_error:
        print(f"    error: {memory_error}")
    print("  Memory files:")
    for name, status in memory_files.items():
        print(f"    - {name}.json: {status}")
    print("  Log files:")
    for name, status in log_status.items():
        print(f"    - {name}: {status}")
    print(f"  Lucifer: {config.LUCIFER_MODEL_NAME} @ {config.LUCIFER_URL}")
    print(f"  Obi:     {config.OBI_MODEL_NAME} @ {config.OBI_URL}")
    print("=" * 72)

    return SI1Runtime(
        lucifer=lucifer,
        obi=obi,
        listener=listener,
        speaker=speaker,
        memorizer=memorizer,
        updater=updater,
        archiver=archiver,
        prompt_engine=prompt_engine,
        memory=memory,
        logger=logger,
        duel_log=duel_log,
        runtime=runtime,
        facts=facts,
        archive=archive,
    )


# =================================================================== main
async def amain() -> None:
    runtime = await build_runtime()
    # Both Generate instances need their aiohttp sessions opened/closed.
    # Without `async with runtime.obi.generate`, the second Obi HTTP call
    # asserts because _session is None.
    async with runtime.lucifer, runtime.obi.generate:
        await runtime.run()


def main() -> None:
    try:
        asyncio.run(amain())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()