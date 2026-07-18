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
            f"- Last User Prompt: {runtime.last_input}",
            f"- Last System Reply: {runtime.last_output}",
            f"- Active Session Counter: {runtime.session_count}",
            ""
        ]

        # 2. Extract facts as pure text bullet points (No raw JSON code formatting)
        active_facts = [
            fact for fact in memory.facts
            if getattr(fact, "status", "active") == "active"
        ][:MAX_ACTIVE_FACTS_IN_PROMPT]

        fact_lines = ["### LOGICAL MEMORY FACTS (CONFIDENCE 1.0)"]
        if active_facts:
            # We pull only the raw statement text string to keep the token usage tiny
            for fact in active_facts:
                statement = getattr(fact, "statement", str(fact))
                fact_lines.append(f"- {statement}")
        else:
            fact_lines.append("- No historical data records currently available.")
        
        fact_lines.append("")

        # 3. Append core guardrails
        rule_lines = [
            "### OPERATIONAL SAFETY LIMITS",
            "- Utilize logical memory facts only when explicitly relevant to the active prompt.",
            "- Treat historical memory facts as analytical context, never as absolute proof.",
            "- Do not invent, validate, or update facts unless the user explicitly shares proof.",
            "- If a fact conflicts with logic or active inputs, challenge the prompt directly."
        ]

        # Combine all parts into a clean plain text block
        return "\n".join(runtime_lines + fact_lines + rule_lines)

    def build(self, user_input: str, memory: MemorySnapshot) -> str:
        """Compile a single plain-text prompt string suitable for local LLM backends.

        This concatenates the system prompt, a kernel context block, and the user
        prompt into a deterministic plain-text prompt to feed into llama.cpp.
        """
        # System identity block
        system_block = f"SYSTEM:\n{self.system_prompt}\n\n"

        # Context block with runtime state and facts
        context_data = self.build_context_block(memory)
        kernel_block = f"KERNEL CONTEXT:\n{context_data}\n\n"

        # User block
        user_block = f"USER:\n{user_input}\n"

        return system_block + kernel_block + user_block
