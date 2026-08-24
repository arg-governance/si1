Migration steps to switch from a legacy HTTP chat server to llama.cpp (llama-cpp-python)

1. Install Python bindings for llama.cpp:

   pip install "llama-cpp-python"

2. Obtain a GGML-format model compatible with llama.cpp (eg. ggml-model-q4_0.bin).
   Place the model file under `./models/` or another directory and set the path
   via environment variable `SI1_LLAMA_MODEL`.

3. Tune thread count if needed via `SI1_LLAMA_THREADS` environment variable.

4. The runtime now uses `LLM_BACKEND = "llama_cpp"` by default. If you still
   have a legacy HTTP chat server and want to use it, change `LLM_BACKEND` in
   `config.py` to an appropriate value and implement the legacy HTTP path (not
   included in this migration).

5. Notes:
   - The prompt engine now compiles prompts to a single plain-text string
     rather than a ChatML array (suitable for local llama.cpp models).
   - Internal components that previously relied on streaming output may see
     synchronous, non-streamed responses depending on your local model and
     the `llama-cpp-python` version. Streaming could be added via the
     library's streaming iterator if desired.
