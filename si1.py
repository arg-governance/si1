""" 'SI-1 command-line runtime entrypoint to the Architect.' """

from __future__ import annotations

from time import perf_counter
from typing import Any

from archive_manager import ArchiveManager
from config import APP_NAME, EXIT_COMMANDS, RUNTIME_VERSION
from fact_extractor import RegexFactExtractor
from fact_validator import FactValidator
from logger import Logger, RunLogEvent
from memory_store import MemoryStore
from models import MemoryDelta, MemorySnapshot, utc_timestamp
from prompt_engine import PromptEngine
from runtime_components import Generate, Listen, Memorize, ObserverV1, Speak, Update


class SI1Runtime:
    """Single-threaded SI-1 orchestration runtime."""

    def __init__(
        self,
        memory_store: MemoryStore,
        listen: Listen,
        prompt_engine: PromptEngine,
        generate: Generate,
        speak: Speak,
        memorize: Memorize,
        observer: ObserverV1,
        update: Update,
        logger: Logger,
    ):
        self.memory_store = memory_store
        self.listen = listen
        self.prompt_engine = prompt_engine
        self.generate = generate
        self.speak = speak
        self.memorize = memorize
        self.observer = observer
        self.update = update
        self.logger = logger

    def run(self) -> None:
        """Run the continuous CLI interaction loop."""
        memory = self.memory_store.load()
        print(f"\n{APP_NAME} Runtime {RUNTIME_VERSION}\n")

        while True:
            try:
                user_input = self.listen.run()
            except (EOFError, KeyboardInterrupt):
                self.memory_store.save(memory)
                print()
                break

            if user_input.lower() in EXIT_COMMANDS:
                self.memory_store.save(memory)
                break

            memory = self.run_iteration(user_input, memory)

    def run_iteration(self, user_input: str, memory: MemorySnapshot) -> MemorySnapshot:
        """Execute one SI-1 turn and return the updated memory snapshot."""
        total_started = perf_counter()
        timings: dict[str, float] = {}
        warnings: list[str] = []
        errors: list[str] = []
        anomalies: list[str] = []

        before = memory.clone()
        generated_prompt = ""
        model_output = ""

        try:
            # --- PHASE 1: OBSERVER LOGICAL VERIFICATION FIRST ---
            observer_started = perf_counter()
            # Observer evaluates the user input against historical memory blocks
            report = self.observer.evaluate(user_input, "", memory)
            timings["observer_ms"] = self._elapsed_ms(observer_started)

            if report.overall_assessment in {"revise", "escalate", "anomaly"}:
                warnings.append(f"Observer prompt flag: {report.overall_assessment}")
                # Inject the observer's warning directly into the prompt stream
                if report.recommendation:
                    user_input = f"[SI-1 Structural Note: {report.recommendation}]\n{user_input}"

            # --- PHASE 2: PROMPT CONTEXT TUNING ---
            generated_prompt = self.prompt_engine.build(user_input, memory)

            # --- PHASE 3: GENERATE & STREAM RESPONSE ---
            # Your generate.run should accept a callback or handle the token streaming 
            # so Lucifer speaks interactively without waiting for a massive buffer.
            generation = self.generate.run(generated_prompt)
            timings["generation_ms"] = generation.elapsed_ms
            warnings.extend(generation.warnings)
            if generation.error:
                errors.append(generation.error)
            model_output = generation.output

            # Let the system print/stream the output to the terminal interface
            self.speak.run(model_output)

            # --- PHASE 4: STRUCTURAL MEMORY DEPOSIT ---
            memory_started = perf_counter()
            # Ensure your memorize implementation triggers the LLM fact extraction config
            memorize_result = self.memorize.update(memory, user_input, model_output)
            warnings.extend(memorize_result.warnings)
            
            self.update.run(memory, user_input, model_output)
            timings["memory_update_ms"] = self._elapsed_ms(memory_started)

            # --- PHASE 5: HARDWARE STATE PERSISTENCE ---
            save_started = perf_counter()
            saved = self.memory_store.save(memory)
            timings["save_ms"] = self._elapsed_ms(save_started)
            if not saved:
                errors.append("Memory save failed")

            after = memory.clone()
            delta = MemoryDelta.compare(before, after)
            timings["total_loop_ms"] = self._elapsed_ms(total_started)

            self._log_iteration(
                user_input=user_input,
                generated_prompt=generated_prompt,
                model_output=model_output,
                before=before,
                after=after,
                new_facts=[fact.to_dict() for fact in memorize_result.new_facts],
                delta=delta,
                timings=timings,
                warnings=warnings,
                errors=errors,
                anomalies=anomalies,
            )
            return memory
        except Exception as e:
            errors.append(f"Iteration error: {str(e)}")
            self.logger.log_failure(f"SI-1 iteration failed: {e}")
            return memory

    def _elapsed_ms(self, started: float) -> float:
        return round((perf_counter() - started) * 1000, 3)

    def _log_iteration(
        self,
        user_input: str,
        generated_prompt: str,
        model_output: str,
        before: MemorySnapshot,
        after: MemorySnapshot,
        new_facts: list[dict[str, Any]],
        delta: MemoryDelta,
        timings: dict[str, float],
        warnings: list[str],
        errors: list[str],
        anomalies: list[str],
    ) -> None:
        """Persist a structured run-log event for this iteration."""
        event = RunLogEvent(
            timestamp=utc_timestamp(),
            user_input=user_input,
            generated_prompt=generated_prompt,
            model_output=model_output,
            runtime_before=before.to_dict(),
            runtime_after=after.to_dict(),
            facts_before=before.facts_to_list(),
            facts_after=after.facts_to_list(),
            new_facts=new_facts,
            memory_delta=delta.to_dict(),
            execution_time_ms=timings,
            warnings=warnings,
            errors=errors,
            anomalies=anomalies,
        )
        self.logger.log(event)


def build_runtime() -> SI1Runtime:
    """Construct SI-1 runtime dependencies."""
    logger = Logger()
    archive_manager = ArchiveManager()
    memory_store = MemoryStore(logger=logger)
    fact_extractor = RegexFactExtractor()
    fact_validator = FactValidator()

    return SI1Runtime(
        memory_store=memory_store,
        listen=Listen(),
        prompt_engine=PromptEngine(),
        generate=Generate(),
        speak=Speak(),
        memorize=Memorize(fact_extractor, fact_validator),
        observer=ObserverV1(),
        update=Update(archive_manager),
        logger=logger,
    )


def main() -> None:
    runtime = build_runtime()
    runtime.run()


if __name__ == "__main__":
    main()
