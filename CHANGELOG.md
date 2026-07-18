# SI-1 Changelog

## [Unreleased]

### Pending — Option B (Local llama-cpp-python binding)
- Install `llama-cpp-python` and `requests` into the venv at `c:\Users\Timm\Desktop\SI-1\.venv\`.
- Set `SI1_LLAMA_MODEL` to `e:\SI-1\models\HERETICODER-2.5-3B-IT.i1-Q6_K.gguf` and `SI1_LLAMA_THREADS=8`.
- Restore `Speak.run()` to print model output (currently `pass`).
- Switch `LLM_BACKEND` from `"llama_cpp"` (in-process binding) to `"legacy_http"` once the local binding is verified, or keep `"llama_cpp"` and ensure the model path resolves.
- Note: `llama-cpp-python` requires C++ build tools on Windows; expect a 5–10 minute compile or use a pre-built wheel.

## [2026-07-16] — HTTP backend patch (Option A)

### Changed
- `runtime_components.py`: `Generate` now supports an HTTP backend that talks to the running `llama-server` at `http://127.0.0.1:8080` (OpenAI-compatible `/v1/chat/completions`). Selected automatically when `LLM_BACKEND == "legacy_http"` or when the in-process `llama_cpp` binding fails to initialize.
- `runtime_components.py`: `Speak.run()` now prints model output (was a no-op `pass`).
- `config.py`: `LLM_BACKEND` default remains `"llama_cpp"`; the HTTP path activates as a fallback so the existing config does not need to change.

### Fixed
- Silent generation failures: when the in-process `llama_cpp` binding is unavailable, the HTTP fallback now produces visible output instead of returning an error string that was swallowed by `Speak`.
- Observer and Memorize internal `Generate` calls now route through the same backend-aware path.

### Verified
- `llama-server` running at `http://127.0.0.1:8080` with `HERETICODER-2.5-3B-IT.i1-Q6_K.gguf` loaded.
- `build_runtime()` constructs successfully.
- `si1.py` exits cleanly (exit code 0) and now streams model output to the terminal.
