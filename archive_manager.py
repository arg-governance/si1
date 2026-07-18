"""Archive management for SI-1 session summaries with AI compression."""

from __future__ import annotations

from config import ARCHIVE_SUMMARY_CHARS, MAX_ARCHIVE_SESSIONS
from models import ArchiveEntry, utc_timestamp


class ArchiveManager:
    """Append, summarize, and trim archive entries using structural compression."""

    def __init__(
        self,
        max_sessions: int = MAX_ARCHIVE_SESSIONS,
        summary_chars: int = ARCHIVE_SUMMARY_CHARS,
    ):
        self.max_sessions = max_sessions
        self.summary_chars = summary_chars

    def summarize(self, output: str) -> str:
        """Compress the response using an internal AI loop to fit within constraints."""
        # We import Generate here to avoid circular dependencies in your runtime
        from runtime_components import Generate
        
        # Build a fast, highly deterministic generator (temperature 0.0)
        summarizer = Generate(options={"temperature": 0.0, "num_predict": 150})
        
        prompt = f"""SI-1 System Utility: Context Compression
        Task: Create a highly dense, abstract summary of the given response. 
        Focus strictly on the core logic, structural conclusions, and trade-offs.
        Constraint: Your output must be concise and fit safely under {self.summary_chars} characters.
        
        Response to compress:
        {output}
        """
        
        result = summarizer.run(prompt)
        
        if result.error or not result.output.strip():
            # Fallback to safe string slicing ONLY if the model call fails
            return output[: self.summary_chars]
            
        # Ensure the final output string respects your exact configuration limit
        return result.output.strip()[: self.summary_chars]

    def append(self, archive: list[ArchiveEntry], output: str) -> None:
        archive.append(ArchiveEntry(time=utc_timestamp(), summary=self.summarize(output)))
        self.trim(archive)

    def trim(self, archive: list[ArchiveEntry]) -> None:
        if len(archive) > self.max_sessions:
            del archive[:-self.max_sessions]
