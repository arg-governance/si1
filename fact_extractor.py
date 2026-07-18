"""Fact extraction interfaces and structural pattern matching implementations."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Sequence

from config import FACT_PATTERNS


class AbstractFactExtractor(ABC):
    """Interface for replaceable fact extraction strategies."""

    @abstractmethod
    def extract(self, user_input: str, model_output: str) -> list[str]:
        """Extract raw candidate facts from the interaction."""


class RegexFactExtractor(AbstractFactExtractor):
    """Context-aware regex extractor that preserves structural integrity without corrupting statements."""

    def __init__(self, patterns: Sequence[str] = FACT_PATTERNS):
        self.patterns = tuple(patterns)

    def extract(self, user_input: str, model_output: str) -> list[str]:
        facts = []
        
        # We process user_input and model_output together but track text cleanly
        text = f"{user_input} {model_output}"

        for pattern in self.patterns:
            # Using case-insensitive flag rather than forcing lower() to preserve proper nouns (like name abbreviations)
            for match in re.findall(pattern, text, re.IGNORECASE):
                candidate = match.strip()
                if not candidate:
                    continue
                
                # FIXED: Check the pattern type to avoid blinding pasting "I am" in front of system architecture facts
                if "name" in pattern or "i am" in pattern or "call me" in pattern:
                    facts.append(f"I am {candidate}")
                else:
                    # Preserves the pure structural assertion exactly as written (e.g. "SI-1 utilizes multi-layer governance")
                    facts.append(candidate)

        return facts
