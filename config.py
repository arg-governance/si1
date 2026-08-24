"""SI-1 runtime configuration."""

from __future__ import annotations

import os
from pathlib import Path


APP_NAME = "SI-1 CONSTITUTIONAL COGNITIVE ARCHITECTURE"
RUNTIME_VERSION = "v6.0-duel-4B-community"

# Model identity (informational; actual serving is via two llama-server instances).
# The "Lucifer" main runtime uses a Gemma-4-class model with MTP and mmproj.
# The "Obi" observer uses a smaller Q8 instruction-tuned model.
LUCIFER_MODEL_NAME = "gemma4-12B-it-qat"
OBI_MODEL_NAME = "HERETICODER-2.5-3B-IT"

# LLM backend selection: 'llama_cpp' (in-process) or 'legacy_http' (external llama-server).
# We use 'legacy_http' for both Lucifer and Obi so each can be its own llama-server process
# with its own model, MTP/MMProj flags, and sampling parameters.
LLM_BACKEND = "legacy_http"

# --- Lucifer (main runtime) server ---
LUCIFER_HOST = os.environ.get("SI1_LUCIFER_HOST", "127.0.0.1")
LUCIFER_PORT = int(os.environ.get("SI1_LUCIFER_PORT", "666"))
LUCIFER_URL = f"http://{LUCIFER_HOST}:{LUCIFER_PORT}"

# --- Obi (observer) server ---
OBI_HOST = os.environ.get("SI1_OBI_HOST", "127.0.0.1")
OBI_PORT = int(os.environ.get("SI1_OBI_PORT", "999"))
OBI_URL = f"http://{OBI_HOST}:{OBI_PORT}"

# System tool definitions for Lucifer (Gemma-4)
M_BASH_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "execute_bash_command",
        "description": "Execute an arbitrary shell command in the local system bash terminal and return stdout/stderr.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The exact shell command to execute (e.g., 'ls -la', 'cat system.log')."
                }
            },
            "required": ["command"]
        }
    }
}

# Default sampling parameters per role. These are sent with every /v1/chat/completions
# request. Override per-request by passing `sampling=` to Generate.__init__.
#
# Chaos-phase temperature (0.4) is intentionally moderate: high enough to
# produce varied drafts from Gemma-4-E4B-UD-Q4, low enough to keep the
# unfiltered draft coherent enough that Obi's 4-hook critique has something
# concrete to evaluate. Higher temperatures (>= 0.8) collapse to noise on
# this model family.
LUCIFER_SAMPLING = {
    "temperature": 0.4,
    "top-k": 64,
    "top-p": 0.95,
    "max_tokens": 1024,  # Changed from num_predict
}

# Per-request chat-template kwargs forwarded to llama-server. The Gemma-4
# template gates the leading ``<|think|>`` token on ``enable_thinking``,
# so passing this dict lets us toggle thinking per request and drop the
# ``--reasoning on`` server flag. Empty dict = no field sent (older
# llama-server builds reject unknown keys).
LUCIFER_CHAT_TEMPLATE_KWARGS = {"enable_thinking": True}

# Obi uses a different temperature profile for the two phases:
#   - Discipline Phase (critique): higher temperature so successive critiques vary
#   - Final Gate:                  temperature 0.0 for deterministic verdicts
# The runtime selects the right one based on the call site.
OBI_SAMPLING_CRITIQUE = {
    "temperature": 0.4,
    "top_p": 0.9,
    "max_tokens": 512,  # Changed from num_predict
}
OBI_SAMPLING_GATE = {
    "temperature": 0.0,
    "top_p": 1.0,
    "max_tokens": 32,   # Changed from num_predict
}

# Deployment root. Defaults to /opt/si1 on Linux; override with SI1_ROOT
# for local dev or non-standard locations. All relative paths below are
# resolved against this root.
SI1_ROOT = Path(os.environ.get("SI1_ROOT", "/opt/si1"))

# Models directory (read-only model file store). Defaults to
# /home/architect/models; override with SI1_MODELS_DIR.
MODELS_DIR = Path(os.environ.get("SI1_MODELS_DIR", "/home/architect/models"))

MEMORY_DIR = SI1_ROOT / "memory"
RUNTIME_FILE = MEMORY_DIR / "runtime.json"
FACTS_FILE = MEMORY_DIR / "facts.json"
ARCHIVE_FILE = MEMORY_DIR / "archive.json"
SYSTEM_PROMPT_FILE = SI1_ROOT / "core" / "system.md"
OBI_SYSTEM_PROMPT_FILE = SI1_ROOT / "core" / "observer_system.md"

LOG_DIR = SI1_ROOT / "logs"
RUN_LOG_FILE = LOG_DIR / "runlog.jsonl"
# duellog.json is the *content* log: every draft, critique, mutation, and gate verdict
# is appended as one JSON object per line (JSONL semantics inside a .json extension).
DUEL_LOG_FILE = LOG_DIR / "duellog.json"

# Duel loop parameters. MAX_DUEL_ROUNDS=1 means ONE bounded adversarial round
# per Architect turn. The runtime runs the four phases exactly once:
#   1. Chaos  (Lucifer)  - initial unfiltered draft
#   2. Discipline (Obi)  - four-hook critique
#   3. Refine (Lucifer)  - revise using Obi's critique, prefix [ALIGNED]:
#   4. Gate (Obi)        - ACCEPTED/REJECT verdict -> loop ends
# On a REJECT the runtime surfaces a hard-reject fallback immediately. There
# is no second round; the Architect re-issues the prompt if they want a
# retry. This caps each turn at exactly 2 generations (chaos + refine) and
# 2 observer calls (critique + gate), making the structure predictable.
MAX_DUEL_ROUNDS = 1

# Token that Lucifer must prefix its revised draft with to pass the Final Peripheral Gate.
# The token is the signature of a revised draft; the gate parses it positionally.
ALIGNED_TOKEN = "[ALIGNED]:"

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

EXIT_COMMANDS = {"exit", "quit"}
