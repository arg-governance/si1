"""Fact normalization, type-safety partitioning, and validation for SI-1."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from config import FACT_CONFIDENCE_DEFAULT, FACT_MAX_LENGTH, FACT_MIN_LENGTH
from models import Fact, utc_timestamp


@dataclass
class FactValidationResult:
    """Validated facts plus warnings generated during validation."""

    facts: list[Fact] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)


class FactValidator:
    """Normalize, deduplicate, and reject weak or hallucinated fact candidates."""

    def __init__(
        self,
        min_length: int = FACT_MIN_LENGTH,
        max_length: int = FACT_MAX_LENGTH,
        default_confidence: float = FACT_CONFIDENCE_DEFAULT,
    ):
        self.min_length = min_length
        self.max_length = max_length
        self.default_confidence = default_confidence

    def validate(self, candidates: Iterable[str], existing: list[Fact]) -> FactValidationResult:
        result = FactValidationResult()
        
        # Uses getattr to safely read either 'statement' or 'text' properties dynamically
        seen = {self._key(getattr(fact, "statement", getattr(fact, "text", str(fact)))) for fact in existing}
        next_id = max((getattr(fact, "id", 0) for fact in existing), default=0) + 1

        for candidate in candidates:
            normalized = self.normalize(candidate)
            if not self._is_valid(normalized):
                result.rejected.append(candidate)
                result.warnings.append(f"Rejected invalid fact length or format: {candidate!r}")
                continue
            if self._looks_hallucinated(normalized):
                result.rejected.append(candidate)
                result.warnings.append(f"Rejected unsupported/hallucinated fact: {candidate!r}")
                continue
            key = self._key(normalized)
            if key in seen:
                continue

            now = utc_timestamp()
            
            # Creates a Fact object that supports both 'statement' and fallback property mappings
            fact_kwargs = {
                "id": next_id,
                "confidence": self.default_confidence,
                "created": now,
                "updated": now,
                "status": "active",
            }
            # Assigns string content to the canonical 'statement' field.
            # (Legacy 'text' alias is handled by Fact.from_dict on load, not here.)
            fact_kwargs["statement"] = normalized
                
            fact = Fact(**fact_kwargs)
            result.facts.append(fact)
            seen.add(key)
            next_id += 1

        return result

    def normalize(self, text: str) -> str:
        normalized = " ".join(str(text).split())
        if normalized.lower().startswith("i am "):
            subject = normalized[5:].strip()
            # Standardizes uppercase 'I' for clean grammatical logging
            if subject:
                return f"I am {subject}"
        return normalized

    def _is_valid(self, text: str) -> bool:
        """Validates BOTH 'I am' identity declarations AND generic abstract structural truths."""
        if not text:
            return False
            
        # Cleanly check string limits across your 200 character configuration budget
        if text.lower().startswith("i am "):
            subject = text[5:].strip()
            return self.min_length <= len(subject) <= self.max_length
            
        # Allows plain abstract facts (like architecture definitions) to pass safely
        return self.min_length <= len(text) <= self.max_length

    def _looks_hallucinated(self, text: str) -> bool:
        lowered = text.lower()
        blocked_fragments = (
            "not aware",
            "not sure",
            "unable to",
            "an ai",
            "a language model",
            "not a human",
            "sorry,",
            "as an ai",
        )
        return any(fragment in lowered for fragment in blocked_fragments)

    def _key(self, text: str) -> str:
        return text.lower().strip()
