"""SI-1 runtime configuration."""

from __future__ import annotations

from pathlib import Path


APP_NAME = "SI-1 CONSTITUTIONAL COGNITIVE ARCHITECTURE"
RUNTIME_VERSION = "v5.3beta1-4B-community"

RUNTIME_MODEL = "lucifer2.0:q6_k"
OBSERVER_MODEL = "lucifer"
MODEL = RUNTIME_MODEL

# LLM backend selection: 'llama_cpp' (local) or 'legacy_http' (external chat server)
LLM_BACKEND = "llama_cpp"

# Path to a local llama.cpp / ggml model file (eg. ./models/ggml-model.bin)
import os
LLAMA_CPP_MODEL_PATH = Path(os.environ.get("SI1_LLAMA_MODEL", "./models/ggml-model.bin"))
# Number of threads for llama.cpp runtime (tune for your CPU)
LLAMA_CPP_THREADS = int(os.environ.get("SI1_LLAMA_THREADS", "4"))



MEMORY_DIR = Path("./memory")
RUNTIME_FILE = MEMORY_DIR / "runtime.json"
FACTS_FILE = MEMORY_DIR / "facts.json"
ARCHIVE_FILE = MEMORY_DIR / "archive.json"
SYSTEM_PROMPT_FILE = Path(os.environ.get("SI1_SYSTEM_PROMPT_FILE", "./core/system_prompt_lucifer.txt"))

LOG_DIR = Path("./logs")
RUN_LOG_FILE = LOG_DIR / "runlog.jsonl"
STORAGE_HASH_CHUNK_BYTES = 1024 * 1024

MAX_ACTIVE_FACTS_IN_PROMPT = 6
MAX_ARCHIVE_SESSIONS = 200
ARCHIVE_SUMMARY_CHARS = 800

FACT_CONFIDENCE_DEFAULT = 0.8
FACT_MIN_LENGTH = 2
FACT_MAX_LENGTH = 200
# Expanded to catch structural assertions, architecture rules, and core assignments
FACT_PATTERNS = (
    r"my name is ([a-zA-Z\s'\-]+)",
    r"i am ([a-zA-Z\s'\-]+)",
    r"call me ([a-zA-Z\s'\-]+)",
    r"architecture rule:\s*(.*)",       # Catches explicit architecture changes
    r"system definition:\s*(.*)",     # Catches abstract crypto/system facts
    r"assert truth:\s*(.*)"           # Force-injects an indisputable fact into memory
)

# Structural Extraction Prompt (To be given to the Observer model)
FACT_EXTRACTION_PROMPT = """
You are part of the SI-1 Cognitive Architecture. Analyze the latest user prompt.
Extract any abstract structural truths, identity claims, cryptographic definitions, or immutable rules.
Ignore casual conversation, emotion, or temporary statements.
Output format MUST be a raw JSON array of strings only, or empty array [] if no facts found:
["Fact 1", "Fact 2"]
"""
EXIT_COMMANDS = {"exit", "quit"}
