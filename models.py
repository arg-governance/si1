"""Persistent data models, delta analysis mechanisms, and structure mapping for SI-1."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
import re
from typing import Any


def utc_timestamp() -> str:
    """Return an ISO-8601 timestamp for runtime records."""
    return datetime.now().isoformat()


@dataclass
class RuntimeState:
    """Mutable runtime state persisted between SI-1 turns."""

    last_input: str = ""
    last_output: str = ""
    session_count: int = 0
    turn: int = 0                                # NEW: monotonic turn counter (async runtime)
    last_active_at: str = ""                     # NEW: ISO-8601 of last activity (async runtime)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "RuntimeState":
        if not isinstance(data, dict):
            return cls()
        return cls(
            last_input=str(data.get("last_input", "")),
            last_output=str(data.get("last_output", "")),
            session_count=int(data.get("session_count", 0) or 0),
            turn=int(data.get("turn", 0) or 0),
            last_active_at=str(data.get("last_active_at", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Fact:
    """A structured fact entry stored in memory with unified architectural alignment."""

    id: int
    statement: str  # FIXED: Renamed text to statement to match PromptEngine and Validator definitions
    confidence: float = 0.8
    created: str = field(default_factory=utc_timestamp)
    updated: str = field(default_factory=utc_timestamp)
    status: str = "active"
    type: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Fact":
        # FIXED: Handles input from data sources whether they used the legacy key 'text' or new 'statement'
        raw_statement = data.get("statement", data.get("text", ""))
        return cls(
            id=int(data.get("id", 0) or 0),
            statement=str(raw_statement),
            confidence=float(data.get("confidence", 0.8) or 0.8),
            created=str(data.get("created", utc_timestamp())),
            updated=str(data.get("updated", utc_timestamp())),
            status=str(data.get("status", "active")),
            type=data.get("type"),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if data["type"] is None:
            data.pop("type")
        return data


@dataclass
class ArchiveEntry:
    """A compact persisted summary of one interaction."""

    time: str
    summary: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ArchiveEntry":
        return cls(
            time=str(data.get("time", utc_timestamp())),
            summary=str(data.get("summary", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MemorySnapshot:
    """Complete persisted memory loaded by the runtime with multi-type shape safety."""

    runtime: RuntimeState = field(default_factory=RuntimeState)
    facts: list[Fact] = field(default_factory=list)
    archive: list[ArchiveEntry] = field(default_factory=list)

    def to_runtime_json(self) -> dict[str, Any]:
        return self.runtime.to_dict()

    def to_facts_json(self) -> list[dict[str, Any]]:
        # FIXED: Outputs a clean, lightweight list array matching memory_store compact requirements
        return [fact.to_dict() for fact in self.facts]

    def to_archive_json(self) -> list[dict[str, Any]]:
        # FIXED: Outputs a clean, lightweight list array matching memory_store compact requirements
        return [entry.to_dict() for entry in self.archive]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the full snapshot (runtime + facts + archive) to a single dict."""
        return {
            "runtime": self.runtime.to_dict(),
            "facts": self.to_facts_json(),
            "archive": self.to_archive_json(),
        }

    def facts_to_list(self) -> list[dict[str, Any]]:
        """Alias for to_facts_json() used by the run-log emitter."""
        return self.to_facts_json()

    def clone(self) -> "MemorySnapshot":
        return MemorySnapshot.from_raw(
            self.to_runtime_json(),
            self.to_facts_json(),
            self.to_archive_json(),
        )

    @classmethod
    def from_raw(
        cls,
        runtime_data: dict[str, Any] | None,
        facts_data: Any,
        archive_data: Any,
    ) -> "MemorySnapshot":
        """FIXED: Intelligently accepts database data arrays regardless of nested dictionary wrappers."""

        # 1. Parse Facts safely out of nested objects OR flat lists
        if isinstance(facts_data, dict):
            facts_raw = facts_data.get("facts", [])
        elif isinstance(facts_data, list):
            facts_raw = facts_data
        else:
            facts_raw = []

        # 2. Parse Archives safely out of nested objects OR flat lists
        if isinstance(archive_data, dict):
            archive_raw = archive_data.get("sessions", [])
        elif isinstance(archive_data, list):
            archive_raw = archive_data
        else:
            archive_raw = []

        return cls(
            runtime=RuntimeState.from_dict(runtime_data),
            facts=[Fact.from_dict(item) for item in facts_raw if isinstance(item, dict)],
            archive=[ArchiveEntry.from_dict(item) for item in archive_raw if isinstance(item, dict)],
        )


@dataclass
class MemoryDelta:
    """Structured report of changes between two memory snapshots."""

    added_facts: list[Fact] = field(default_factory=list)
    removed_facts: list[Fact] = field(default_factory=list)
    modified_facts: list[dict[str, Any]] = field(default_factory=list)
    runtime_changes: dict[str, dict[str, Any]] = field(default_factory=dict)
    archive_changes: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def compare(cls, before: MemorySnapshot, after: MemorySnapshot) -> "MemoryDelta":
        before_facts = {fact.id: fact for fact in before.facts}
        after_facts = {fact.id: fact for fact in after.facts}

        added = [fact for fact_id, fact in after_facts.items() if fact_id not in before_facts]
        removed = [fact for fact_id, fact in before_facts.items() if fact_id not in after_facts]
        modified = []
        for fact_id, after_fact in after_facts.items():
            before_fact = before_facts.get(fact_id)
            if before_fact and before_fact.to_dict() != after_fact.to_dict():
                modified.append({
                    "id": fact_id,
                    "before": before_fact.to_dict(),
                    "after": after_fact.to_dict(),
                })

        runtime_changes = {}
        before_runtime = before.runtime.to_dict()
        after_runtime = after.runtime.to_dict()
        for key, before_value in before_runtime.items():
            after_value = after_runtime.get(key)
            if before_value != after_value:
                runtime_changes[key] = {"before": before_value, "after": after_value}

        archive_changes: dict[str, Any] = {}
        if len(before.archive) != len(after.archive):
            archive_changes["count"] = {
                "before": len(before.archive),
                "after": len(after.archive),
            }
        if before.archive != after.archive:
            archive_changes["latest"] = after.archive[-1].to_dict() if after.archive else None

        return cls(
            added_facts=added,
            removed_facts=removed,
            modified_facts=modified,
            runtime_changes=runtime_changes,
            archive_changes=archive_changes,
        )


# ============================================================ Duel loop
# Symbols below were promoted from models.bak.py so runtime_components.py
# and si1.py can import them from `models as M` (the canonical module).


@dataclass
class DuelLogEntry:
    """One row in the duellog.json content stream (JSONL semantics).

    Captures every draft, critique, mutation, gate verdict, and rejection
    across the four-phase loop. ``meta`` is a free-form dict for round-level
    bookkeeping (attempt index, score, latency, etc.) without forcing a
    schema on every call site.
    """

    ts: int                                # Unix epoch seconds
    turn: int                              # SI-1 monotonic turn counter
    round: int                             # Duel round (0 = initial draft)
    kind: str                              # 'draft' | 'critique' | 'mutation' | 'gate' | 'rejection'
    actor: str                             # 'lucifer' | 'obi' | 'runtime'
    text: str                              # The actual generated/parsed text
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DuelVerdict:
    """Result of Obi's Final Peripheral Gate.

    Parsed from the strict single-line protocol Obi is contractually bound
    to emit: ``ACCEPTED`` or ``REJECT\\nreason: ...``.
    """

    accepted: bool
    reason: str = ""

    @classmethod
    def from_gate_text(cls, text: str) -> "DuelVerdict":
        """Parse Obi's gate output. Tolerant of whitespace and casing.

        A REJECT is only valid when Obi supplies a specific, non-generic reason
        line. Generic fallbacks like ``no reason provided`` are treated as a
        failed parse so the runtime can force a hard reject with an explicit
        reason from Obi's own verdict logic.
        """
        if not text:
            return cls(accepted=False, reason="empty gate response")

        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if not lines:
            return cls(accepted=False, reason="empty gate response")

        first = lines[0].strip().upper()
        if first == "ACCEPTED":
            return cls(accepted=True, reason="")

        if first == "REJECT":
            reason = ""
            for ln in lines[1:]:
                if ln.lower().startswith("reason"):
                    _, _, after = ln.partition(":")
                    if not after:
                        _, _, after = ln.partition("-")
                    reason = after.strip()
                    break
            if not reason:
                return cls(accepted=False, reason="reject without specific obi reason")
            reason_lower = reason.lower()
            generic_markers = {
                "no reason provided",
                "generic reject",
                "reject without specific reason",
                "no reason",
                "reason missing",
                "empty gate response",
            }
            if reason_lower in generic_markers or reason_lower.startswith("reason:"):
                return cls(accepted=False, reason="reject without specific obi reason")
            if any(token in reason_lower for token in ("hook", "missing", "evidence", "defect", "gap", "contradiction", "unsupported", "fails", "lacks", "invalid", "wrong", "ignored")):
                return cls(accepted=False, reason=reason)
            if len([word for word in reason.split() if len(word) > 3]) >= 3:
                return cls(accepted=False, reason=reason)
            return cls(accepted=False, reason=reason)

        return cls(accepted=False, reason=f"unparseable gate verdict: {lines[0]!r}")


HOOK_NAMES: tuple[str, ...] = ("arrived", "overlooked", "principle", "reevaluate")


@dataclass
class GatePayload:
    """Per-hook engagement signal from Lucifer's revised draft.

    Four bits, in the canonical hook order. Each bit is either
    ``"accepted"`` (the critique was applied) or ``"disagreed"``
    (Lucifer defends a counter-position). The runtime extracts this
    payload from the line immediately following the literal
    ``[ALIGNED]:`` token and uses it to verify per-hook engagement
    rather than relying on token presence alone.
    """

    arrived: str = "accepted"
    overlooked: str = "accepted"
    principle: str = "accepted"
    reevaluate: str = "accepted"

    def as_bits(self) -> list[str]:
        return [self.arrived, self.overlooked, self.principle, self.reevaluate]

    def is_valid(self) -> bool:
        valid = {"accepted", "disagreed"}
        return all(getattr(self, name) in valid for name in HOOK_NAMES)

    @classmethod
    def from_payload_line(cls, line: str) -> "GatePayload":
        """Parse the 4-bit payload line, e.g. ``accepted|accepted|accepted|disagreed``.

        Tolerant of extra whitespace and casing. Any unparseable bit
        defaults to ``"accepted"`` (lenient) but the payload will fail
        ``is_valid()`` if any bit isn't one of the two legal values.
        """
        parts = [p.strip().lower() for p in line.split("|")]
        kwargs = {name: parts[i] if i < len(parts) else "accepted" for i, name in enumerate(HOOK_NAMES)}
        return cls(**kwargs)


def find_aligned_payload(text: str) -> tuple[bool, "GatePayload | None", str]:
    """Extract the ``[ALIGNED]:`` token + 4-bit payload from a revised draft.

    Returns:
        (token_present, payload_or_None, body_without_token_and_payload).
        The body is the revised draft with the leading two lines stripped
        (token line + payload line) when both are present, or just the
        token line stripped when only the token is present. Other leading
        whitespace is preserved.
    """
    if not text:
        return False, None, text
    stripped = text.lstrip()
    if not stripped.startswith("[ALIGNED]:"):
        return False, None, text
    # Drop the token line and locate the next non-empty payload line.
    after_token = stripped[len("[ALIGNED]:"):]
    lines = after_token.splitlines()
    payload_index = next(
        (index for index, line in enumerate(lines) if line.strip()),
        None,
    )
    first = lines[payload_index].strip() if payload_index is not None else ""
    payload = GatePayload.from_payload_line(first)
    if payload.is_valid() and "|" in first:
        body = "\n".join(lines[payload_index + 1:]).lstrip("\n")
    else:
        payload = None
        body = after_token.lstrip("\n")
    return True, payload, body


def find_override(text: str) -> str | None:
    """Return the override line text if the assistant's last turn contains
    a literal ``[OVERRIDE]:`` token, else None. Used by the runtime to
    bypass the "constitutional gate refused" fallback when the Architect
    has explicitly directed the runtime to proceed past a REJECT.
    """
    if not text:
        return None
    for ln in text.splitlines():
        stripped = ln.strip()
        lower = stripped.lower()
        if lower.startswith("[override]:"):
            return stripped[len("[override]:"):].strip()
    return None


def parse_architect_tag(text: str) -> tuple[str, str] | None:
    """Parse direct one-to-one prompts like ``[LUCIFER]: ...`` or ``[OBI]: ...``.

    Returns ``("lucifer", prompt_body)`` or ``("obi", prompt_body)`` when a
    direct tagged prompt is present; otherwise ``None``. A direct tagged prompt
    bypasses the four-phase duel loop and sends the Architect's body directly to
    the named model as a casual one-on-one prompt.
    """
    if not text:
        return None
    # Cursor keys can arrive as ANSI CSI sequences when the tag is edited in
    # a terminal. For example, ``[LUCIFER]`` followed by cursor-right may
    # reach stdin as ``[LUCIFER]\x1b[C:`` and otherwise miss this branch.
    normalized = re.sub(r"\x1b\[[0-9;?]*[ -/]*[@-~]", "", text)
    normalized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", normalized)
    stripped = normalized.strip()
    for name in ("lucifer", "obi"):
        prefix = f"[{name.upper()}]:"
        if stripped.upper().startswith(prefix):
            body = stripped[len(prefix):].strip()
            return (name, body) if body else None
        short_prefix = f"[{name.upper()}]"
        if stripped.upper().startswith(short_prefix):
            body = stripped[len(short_prefix):].lstrip(":").strip()
            return (name, body) if body else None
    return None


# Header used by Obi to introduce his independent read of the Architect's
# prompt (see ``core/observer_system.md`` — Discipline Phase fifth block).
# Case-insensitive; the colon and trailing space are stripped before the
# opinion body. Matched as a stand-alone line so "my view" inside prose
# doesn't trigger a false split.
ARCHITECT_OPINION_HEADER = "my view on the architect's prompt:"


def split_architect_opinion(text: str) -> tuple[str, str | None]:
    """Split Obi's critique into (hooks_only, architect_opinion_or_None).

    Obi's discipline-phase output ends (optionally) with a fifth block
    headed by ``My view on the Architect's prompt:`` on its own line. That
    block is Obi's independent take on the *Architect's prompt* — not on
    Lucifer's draft — and is surfaced to the Architect separately. It is
    NOT fed to Lucifer during the Refined Learning Pass, because Lucifer
    cannot revise the Architect's prompt; only the four hooks can drive
    a revision. Splitting keeps the two concerns clean.

    Returns:
        (hooks_text, opinion_text_or_None). ``hooks_text`` is the full
        critique text if no opinion header is found, or the critique
        text with the opinion block stripped if one is found. The opinion
        text is the body that followed the header line, trimmed of
        leading/trailing whitespace. Empty header with no body returns
        ``(hooks_text, "")`` so the runtime can still log that Obi
        emitted the header but had nothing to add.
    """
    if not text:
        return text, None

    # Walk line-by-line. The opinion block starts at the first line that
    # matches the header (case-insensitive, stripped). Everything from
    # that line onwards is the opinion; everything before is the hooks.
    lines = text.splitlines()
    split_idx: int | None = None
    for i, ln in enumerate(lines):
        if ln.strip().lower() == ARCHITECT_OPINION_HEADER:
            split_idx = i
            break

    if split_idx is None:
        return text, None

    hooks_text = "\n".join(lines[:split_idx]).rstrip()
    opinion_text = "\n".join(lines[split_idx + 1:]).strip()
    return hooks_text, opinion_text or ""


@dataclass
class AlignedMeta:
    """Optional epistemic-status block declared by Lucifer at the end of a draft.

    Parsed from ``[META] … [/META]`` if present. Counts default to 0 when
    the block is absent. ``uncertainty_reasons`` and ``refuse_reasons``
    are one-line reasons matching the corresponding count; they may be
    empty lists when the count is 0.
    """

    facts: int = 0
    inferences: int = 0
    uncertainties: int = 0
    refuses: int = 0
    uncertainty_reasons: list[str] = field(default_factory=list)
    refuse_reasons: list[str] = field(default_factory=list)

    @classmethod
    def from_text(cls, text: str) -> "AlignedMeta | None":
        """Extract the [META] block. Returns None if absent or malformed.
        On partial parse, returns a meta with the fields that did parse.
        """
        if not text or "[META]" not in text:
            return None
        try:
            body = text.split("[META]", 1)[1].split("[/META]", 1)[0]
        except IndexError:
            return None

        # Ensure regex or robust string partitioning handles inline trailing metadata text
        def _parse_int(val_str: str) -> int:
            if not val_str:
                return 0
            # Strip trailing inline fields like ", inferences: 2..." if present
            base_token = val_str.split(',')[0].strip()
            # Extract leading consecutive numeric digits safely
            import re
            match = re.search(r'\d+', base_token)
            return int(match.group()) if match else 0

        # ... (implementation of clean_int used in parsing)
        # Apply clean_int(value) to meta.facts, meta.inferences, 
        # meta.uncertainties, and meta.refuses during parsing

        meta = cls()
        current_list: list[str] | None = None
        for raw in body.splitlines():
            line = raw.strip()
            if not line:
                continue
            key, sep, value = line.partition(":")
            if not sep:
                continue
            key = key.strip().lower()
            value = value.strip()
            
            if key == "facts":
                meta.facts = max(0, _parse_int(value))
            elif key == "inferences":
                meta.inferences = max(0, _parse_int(value))
            elif key == "uncertainties":
                meta.uncertainties = max(0, _parse_int(value))
                meta.uncertainty_reasons = []
                current_list = meta.uncertainty_reasons
            elif key == "refuses":
                meta.refuses = max(0, _parse_int(value))
                meta.refuse_reasons = []
                current_list = meta.refuse_reasons
            elif key in ("- reason", "- r") and current_list is not None:
                current_list.append(value)
            elif current_list is not None and value:
                # Continuation of the most recent reason (multi-line)
                if current_list:
                    current_list[-1] = (current_list[-1] + " " + value).strip()
        return meta


    def to_dict(self) -> dict[str, Any]:
        return {
            "facts": self.facts,
            "inferences": self.inferences,
            "uncertainties": self.uncertainties,
            "refuses": self.refuses,
            "uncertainty_reasons": list(self.uncertainty_reasons),
            "refuse_reasons": list(self.refuse_reasons),
        }