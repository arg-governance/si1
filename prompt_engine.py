"""Prompt assembly and structural role formatting for SI-1 ChatML pipelines."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from config import MAX_ACTIVE_FACTS_IN_PROMPT, SYSTEM_PROMPT_FILE
from models import Fact, MemorySnapshot


class PromptEngine:
    """Build structured conversational payload arrays passed to the ChatML pipeline."""

    def __init__(self, system_prompt_path: Path = SYSTEM_PROMPT_FILE):
        self.system_prompt_path = Path(system_prompt_path)
        self.system_prompt = self.load_system_prompt()

    def load_system_prompt(self) -> str:
        try:
            if not self.system_prompt_path.exists():
                return "Core SI-1 Runtime Active."
            return self.system_prompt_path.read_text(encoding="utf-8").strip()
        except OSError:
            return "Core SI-1 Runtime Active."

    def build_context_block(self, memory: MemorySnapshot) -> str:
        """Assembles a clean, plain-text injection block containing facts and states."""
        # 1. Map current runtime statistics
        runtime = memory.runtime
        runtime_lines = [
            "### RUNTIME STATE",
            f"- Turn: {runtime.turn}",
            f"- Last Active: {runtime.last_active_at or 'n/a'}",
            f"- Last User Prompt: {runtime.last_input}",
            f"- Last System Reply: {runtime.last_output}",
            ""
        ]

        # 2. Extract facts as pure text bullet points (No raw JSON code formatting)
        # Show the MOST RECENT active facts, not the oldest. ``memory.facts``
        # is appended chronologically (oldest first), so the previous slice
        # ``[:MAX_ACTIVE_FACTS_IN_PROMPT]`` gave Lucifer the *earliest* facts
        # — the opposite of what a recency-aware prompt wants. Take from the
        # tail and reverse to keep newest-first ordering.
        active_facts = [
            fact for fact in memory.facts
            if getattr(fact, "status", "active") == "active"
        ]
        active_facts = active_facts[-MAX_ACTIVE_FACTS_IN_PROMPT:][::-1]

        fact_lines = ["### LOGICAL MEMORY FACTS (CONFIDENCE 0.8)"]
        if active_facts:
            # We pull only the raw statement text string to keep the token usage tiny
            for fact in active_facts:
                statement = getattr(fact, "statement", str(fact))
                fact_lines.append(f"- {statement}")
        else:
            fact_lines.append("- No historical data records currently available.")

        fact_lines.append("")

        # 3. Surface the most recent archive entry (best-effort). The
        # archive is a list of summarized past turns; showing the latest
        # one gives Lucifer continuity across sessions without dumping
        # the full history into the context. Older entries live on disk
        # for the auditor (``memory/archive.json``).
        archive_lines = ["### MOST RECENT ARCHIVED SESSION"]
        if memory.archive:
            latest = memory.archive[-1]
            archive_lines.append(
                f"- [{latest.time}] {latest.summary}"
            )
        else:
            archive_lines.append("- No prior sessions archived yet.")
        archive_lines.append("")

        # 4. Append core guardrails
        rule_lines = [
            "### OPERATIONAL SAFETY LIMITS",
            "- Utilize logical memory facts only when explicitly relevant to the active prompt.",
            "- Treat historical memory facts as analytical context, never as absolute proof.",
            "- Do not invent, validate, or update facts unless the user explicitly shares proof.",
            "- If a fact conflicts with logic or active inputs, challenge the prompt directly."
        ]

        # Combine all parts into a clean plain text block
        return "\n".join(runtime_lines + fact_lines + archive_lines + rule_lines)

    def build(
        self,
        system_prompt: str,
        context_block: str,
        user_input: str,
    ) -> str:
        """Compile a single plain-text prompt string.

        Kept for back-compat with call sites that have not yet migrated
        to :meth:`build_messages`. The new code path is preferred —
        passing a real ``messages`` list lets ``llama-server`` apply the
        model's chat template (Gemma-4's ``<|turn>role\n...<turn|>``)
        instead of mashing everything into one user blob.
        """
        sys_text = system_prompt if system_prompt else self.system_prompt
        system_block = f"SYSTEM:\n{sys_text}\n\n"
        kernel_block = f"KERNEL CONTEXT:\n{context_block}\n\n"
        user_block = f"USER:\n{user_input}\n"
        return system_block + kernel_block + user_block

    def build_messages(
        self,
        system_prompt: str,
        context_block: str,
        user_input: str,
        prior_turns: list[dict[str, str]] | None = None,
    ) -> list[dict[str, str]]:
        """Build a real ChatML ``messages`` list for the four-phase loop.

        Returns a list of ``{"role": ..., "content": ...}`` dicts ready
        to be passed to ``Generate.run_messages`` / ``astream_messages``.
        ``llama-server`` applies the model's chat template to this list,
        so the model sees the system prompt as a real ``system`` role
        (not as more user text), prior turns keep their roles, and the
        kernel context lives in the latest user turn alongside the
        Architect's prompt.

        Args:
            system_prompt: Constitutional system prompt (Lucifer's
                ``core/system.md``). Falls back to the prompt loaded at
                construction when empty.
            context_block: Kernel-context block (runtime state, facts,
                archive, safety limits) — pre-built by
                :meth:`build_context_block`. Goes inside the *latest*
                user turn so it travels with the prompt.
            user_input: The Architect's most recent prompt (or, for
                refine-phase, a wrapper around Obi's critique).
            prior_turns: Optional list of earlier turns
                (``{"role": "user"|"assistant", "content": "..."}``)
                to thread into the conversation. Used by the revise
                phase to keep the chaos draft + Obi's critique as
                real assistant / user turns rather than concatenated
                blobs.
        """
        sys_text = system_prompt if system_prompt else self.system_prompt
        messages: list[dict[str, str]] = [
            {"role": "system", "content": sys_text},
        ]
        if prior_turns:
            messages.extend(prior_turns)
        # Kernel context is part of the *latest* user turn (the one
        # the model is responding to). For prior user turns the kernel
        # context is irrelevant — the model already saw it when those
        # turns were produced.
        latest_user = (
            f"KERNEL CONTEXT:\n{context_block}\n\n"
            f"USER:\n{user_input}"
        )
        messages.append({"role": "user", "content": latest_user})
        return messages
