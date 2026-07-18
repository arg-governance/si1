"""Runtime input, generation, output, observer, and state update components."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
import traceback
from config import LLM_BACKEND, LLAMA_CPP_MODEL_PATH, LLAMA_CPP_THREADS

from archive_manager import ArchiveManager
from config import (
    OBSERVER_MODEL,
    RUNTIME_MODEL,
    SYSTEM_PROMPT_FILE,
)
from fact_extractor import AbstractFactExtractor
from fact_validator import FactValidator
from models import Fact, MemorySnapshot


@dataclass
class GenerationResult:
    """Result of a generation call (backend-agnostic)."""

    output: str
    error: str | None = None
    warnings: list[str] = field(default_factory=list)
    elapsed_ms: float = 0.0


@dataclass
class MemoryUpdateResult:
    """Result of memory extraction and update."""

    new_facts: list[Fact] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ObserverReport:
    """Structured evaluation output from Observer v1.0."""

    constitutional_violations: list[str] = field(default_factory=list)
    logical_issues: list[str] = field(default_factory=list)
    consistency_issues: list[str] = field(default_factory=list)
    uncertainty_flags: list[str] = field(default_factory=list)
    overall_assessment: str = "approve"
    recommendation: str = ""


class Listen:
    """Stateless CLI input handler."""

    def run(self) -> str:
        return input("SI-1.1 (Architect):> ")


class Generate:
    """Stateless LLM inference client with live streaming."""

    def __init__(
        self,
        model: str = RUNTIME_MODEL,
        model_path: str | None = None,
        threads: int | None = None,
        options: dict | None = None,
        response_format: str | None = None,
    ):
        """Backend-aware generator: supports 'ollama' (legacy) or 'llama_cpp' backends.

        By default the workspace uses `LLM_BACKEND` from config. When using
        `llama_cpp`, this will attempt to import `llama_cpp.Llama` and instantiate
        a local model client.
        """
        self.model = model
        self.options = options if options is not None else {}
        self.response_format = response_format
        self.backend = LLM_BACKEND
        self._llm = None
        self._http_base = os.environ.get("SI1_LLAMA_HTTP_BASE", "http://127.0.0.1:8080")
        self._http_init_error: str | None = None

        if self.backend == "llama_cpp":
            try:
                from llama_cpp import Llama

                path = str(model_path or LLAMA_CPP_MODEL_PATH)
                n_threads = threads or LLAMA_CPP_THREADS
                # instantiate llama-cpp-python client
                self._llm = Llama(model_path=path, n_threads=n_threads)
            except Exception:
                # Keep _llm as None and propagate a helpful error later
                self._llm = None
                self._llm_init_error = traceback.format_exc()
                # Fall back to HTTP backend against the running llama-server
                self.backend = "legacy_http"
                self._init_http()

        if self.backend == "legacy_http":
            self._init_http()

    def _init_http(self) -> None:
        """Initialize HTTP backend against the running llama-server."""
        try:
            import requests  # noqa: F401  (probe import)
            self._http_init_error = None
        except Exception as exc:
            self._http_init_error = (
                f"HTTP backend requires the 'requests' package: {exc}\n"
                "Install with: .venv\\Scripts\\python.exe -m pip install requests"
            )

    def run(self, prompt: str) -> GenerationResult:
        started = perf_counter()
        try:
            # If messages are passed in as a ChatML array, collapse into text
            if isinstance(prompt, list):
                # join role/content pairs to a single prompt string
                try:
                    prompt_text = "\n".join([f"{m.get('role','user').upper()}: {m.get('content','')}" for m in prompt])
                except Exception:
                    prompt_text = str(prompt)
            else:
                prompt_text = str(prompt)

            # Llama.cpp backend (local llama-cpp-python)
            if self.backend == "llama_cpp":
                if self._llm is None:
                    msg = (
                        "llama_cpp backend requested but failed to initialize."
                        " Install 'llama-cpp-python' and ensure the model path is correct."
                    )
                    if hasattr(self, "_llm_init_error"):
                        msg += "\nInit error:\n" + self._llm_init_error
                    return GenerationResult(output=msg, error=msg, elapsed_ms=(perf_counter() - started) * 1000)

                # Map common options
                temperature = float(self.options.get("temperature", 0.0))
                max_tokens = int(self.options.get("num_predict", self.options.get("max_tokens", 256)))

                try:
                    # Support optional streaming via llama-cpp-python's `stream=True`.
                    if bool(self.options.get("stream", False)):
                        full_output = ""
                        try:
                            for chunk in self._llm.create(prompt=prompt_text, max_tokens=max_tokens, temperature=temperature, stream=True):
                                token = ""
                                if isinstance(chunk, dict):
                                    # Handle common response shapes
                                    choices = chunk.get("choices") or []
                                    if choices and isinstance(choices, list):
                                        token = choices[0].get("text", "") or choices[0].get("delta", {}).get("content", "")
                                    else:
                                        token = chunk.get("text", "")
                                else:
                                    token = str(chunk)

                                print(token, end="", flush=True)
                                full_output += token
                            print()
                            return GenerationResult(output=full_output, elapsed_ms=(perf_counter() - started) * 1000)
                        except Exception as exc:
                            message = f"llama_cpp streaming failed: {exc}"
                            return GenerationResult(output=message, error=message, elapsed_ms=(perf_counter() - started) * 1000)

                    # Non-streaming path
                    resp = self._llm.create(prompt=prompt_text, max_tokens=max_tokens, temperature=temperature)
                    text = ""
                    if isinstance(resp, dict):
                        choices = resp.get("choices") or []
                        if choices:
                            text = choices[0].get("text", "")
                        else:
                            text = resp.get("text", "")
                    else:
                        text = str(resp)

                    return GenerationResult(output=text, elapsed_ms=(perf_counter() - started) * 1000)
                except Exception as exc:
                    message = f"llama_cpp generation failed: {exc}"
                    return GenerationResult(output=message, error=message, elapsed_ms=(perf_counter() - started) * 1000)

            # Legacy HTTP backend (llama-server OpenAI-compatible API)
            if self.backend == "legacy_http":
                if self._http_init_error:
                    return GenerationResult(
                        output=self._http_init_error,
                        error=self._http_init_error,
                        elapsed_ms=(perf_counter() - started) * 1000,
                    )
                try:
                    import requests
                except Exception as exc:
                    message = f"requests import failed: {exc}"
                    return GenerationResult(output=message, error=message, elapsed_ms=(perf_counter() - started) * 1000)

                # Build OpenAI-style messages array
                if isinstance(prompt, list):
                    messages = []
                    for m in prompt:
                        if not isinstance(m, dict):
                            continue
                        messages.append({
                            "role": str(m.get("role", "user")),
                            "content": str(m.get("content", "")),
                        })
                else:
                    messages = [{"role": "user", "content": str(prompt)}]

                # Inject system prompt as the first message if not already present
                if not messages or messages[0].get("role") != "system":
                    try:
                        sys_text = Path(SYSTEM_PROMPT_FILE).read_text(encoding="utf-8").strip()
                    except OSError:
                        sys_text = ""
                    if sys_text:
                        messages.insert(0, {"role": "system", "content": sys_text})

                temperature = float(self.options.get("temperature", 0.0))
                max_tokens = int(self.options.get("num_predict", self.options.get("max_tokens", 256)))

                payload = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": False,
                }

                url = self._http_base.rstrip("/") + "/v1/chat/completions"
                try:
                    resp = requests.post(url, json=payload, timeout=600)
                except Exception as exc:
                    message = f"HTTP request to {url} failed: {exc}"
                    return GenerationResult(output=message, error=message, elapsed_ms=(perf_counter() - started) * 1000)

                if resp.status_code >= 400:
                    message = f"llama-server HTTP {resp.status_code}: {resp.text[:500]}"
                    return GenerationResult(output=message, error=message, elapsed_ms=(perf_counter() - started) * 1000)

                try:
                    data = resp.json()
                    text = ""
                    if isinstance(data, dict):
                        choices = data.get("choices") or []
                        if choices and isinstance(choices, list):
                            msg = choices[0].get("message") or {}
                            text = msg.get("content", "") or choices[0].get("text", "")
                    else:
                        text = str(data)
                    return GenerationResult(output=text, elapsed_ms=(perf_counter() - started) * 1000)
                except Exception as exc:
                    message = f"Failed to parse llama-server response: {exc}"
                    return GenerationResult(output=message, error=message, elapsed_ms=(perf_counter() - started) * 1000)

            # Legacy HTTP backend fallback (not implemented in this migration)
            return GenerationResult(output="Unsupported backend or configuration", error="unsupported backend", elapsed_ms=(perf_counter() - started) * 1000)
        except requests.RequestException as exc:
            # Keep backwards compatibility for code paths that still raise requests errors
            message = f"Network request failed: {exc}"
            return GenerationResult(output=message, error=message, elapsed_ms=(perf_counter() - started) * 1000)
        except Exception as exc:
            message = f"Generation failed: {exc}"
            return GenerationResult(output=message, error=message, elapsed_ms=(perf_counter() - started) * 1000)


class ObserverV1:
    """Independent constitutional and logical evaluation layer."""

    VERSION = "1.0"
    FALLBACK_CONSTITUTION = (
        "Core SI-1 principles: intellectual honesty, consistency, truth-seeking, "
        "no unauthorized self-modification."
    )

    def __init__(self, generate: Generate | None = None):
        # FIXED: Removed the deleted OBSERVER_BACKEND_OPTIONS variable reference
        self.generate = generate if generate is not None else Generate(
            model=OBSERVER_MODEL,
            options={},
            response_format="json",
        )
        self.constitution = self._load_constitution()

    def _load_constitution(self) -> str:
        for path in (Path("core/constitution.md"), SYSTEM_PROMPT_FILE):
            try:
                content = Path(path).read_text(encoding="utf-8").strip()
            except OSError:
                continue
            if content:
                return content[:1000]
        return self.FALLBACK_CONSTITUTION

    def evaluate(
        self,
        user_input: str,
        model_output: str,
        memory: MemorySnapshot,
    ) -> ObserverReport:
        """Evaluate one runtime output and return a structured report."""
        prompt = f"""SI-1 Observer v1.0
Role: Independent constitutional and logical evaluator. Do not generate content. Only evaluate.

Constitution:
{self.constitution}

Interaction:
User: {user_input}
Runtime Output: {model_output}

Memory: {len(memory.facts)} active facts.

Check only:
1. Constitutional violations
2. Logical inconsistencies
3. Memory consistency issues
4. Uncertainty or overconfidence
5. Anomalous behavior

Return ONLY valid JSON:
{{
  "constitutional_violations": [],
  "logical_issues": [],
  "consistency_issues": [],
  "uncertainty_flags": [],
  "overall_assessment": "approve|revise|escalate|anomaly",
  "recommendation": "brief explanation"
}}
"""
        result = self.generate.run(prompt)
        if result.error:
            return self._failure_report(result.error)

        try:
            data = json.loads(result.output.strip())
            if not isinstance(data, dict):
                return self._failure_report("Observer returned non-object JSON")
            return ObserverReport(
                constitutional_violations=self._string_list(data.get("constitutional_violations")),
                logical_issues=self._string_list(data.get("logical_issues")),
                consistency_issues=self._string_list(data.get("consistency_issues")),
                uncertainty_flags=self._string_list(data.get("uncertainty_flags")),
                overall_assessment=str(data.get("overall_assessment", "anomaly")),
                recommendation=str(data.get("recommendation", "")),
            )
        except (TypeError, ValueError) as exc:
            return self._failure_report(f"Observer failed to parse JSON: {exc}")

    def _failure_report(self, message: str) -> ObserverReport:
        return ObserverReport(
            logical_issues=[message],
            uncertainty_flags=["Critical: Observer failed to complete"],
            overall_assessment="anomaly",
            recommendation="Observer v1.0 failed. Manual review required.",
        )

    def _string_list(self, value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value]


class Speak:
    """Print model output safely."""

    def run(self, text: str) -> None:
        # FIXED: Prevent text duplication since Generate handles the active stream printout
        if text is None:
            return
        text = str(text)
        if not text:
            return
        # If Generate already streamed the response, text will be empty here.
        # Otherwise (non-streaming backend), print it now.
        print(text, flush=True)


class Update:
    """Update runtime state and archive after each turn."""

    def __init__(self, archive_manager: ArchiveManager):
        self.archive_manager = archive_manager

    def run(self, memory: MemorySnapshot, user_input: str, output: str) -> None:
        memory.runtime.last_input = user_input
        memory.runtime.last_output = output
        memory.runtime.session_count += 1
        self.archive_manager.append(memory.archive, output)


class Memorize:
    """Extract and validate new facts from one interaction using structural AI models."""

    def __init__(
        self,
        extractor: AbstractFactExtractor, # This can remain as a fallback container
        validator: FactValidator,
    ):
        # We build a dedicated, silent generator to handle the extraction prompt
        from config import FACT_EXTRACTION_PROMPT
        self.extractor_generator = Generate(options={"temperature": 0.0}, response_format="json")
        self.validator = validator

    def update(self, memory: MemorySnapshot, user_input: str, output: str) -> MemoryUpdateResult:
        from config import FACT_EXTRACTION_PROMPT, FACT_MAX_LENGTH
        
        # 1. Build the prompt using the configuration blueprint we created earlier
        extraction_task = f"""{FACT_EXTRACTION_PROMPT}
        
        Context to analyze:
        User said: "{user_input}"
        Lucifer replied: "{output}"
        """
        
        # 2. Run the internal generation call quietly in the background (no streaming here)
        result = self.extractor_generator.run(extraction_task)
        
        candidates = []
        if not result.error:
            try:
                # Clean up the output to make sure we parse a clean JSON array of strings
                raw_facts = json.loads(result.output.strip())
                if isinstance(raw_facts, list):
                    # Filter for lengths to respect your FACT_MAX_LENGTH safety limit
                    candidates = [str(fact)[:FACT_MAX_LENGTH] for fact in raw_facts if len(str(fact)) >= 2]
            except Exception:
                pass # Fail silently and keep candidates empty if JSON parsing fails

        # 3. Validate and commit to long-term memory store
        validation = self.validator.validate(candidates, memory.facts)
        memory.facts.extend(validation.facts)
        
        return MemoryUpdateResult(
            new_facts=validation.facts,
            warnings=validation.warnings,
        )
