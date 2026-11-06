# Model Discrepancy Notes

> Migration document. Will be archived once the runtime locks to a single
> canonical Lucifer model and `config.py` rejects the others.

## Canonical configuration (per `README.md` §III and `config.py`)

| Role | Model | Quantization | Server port |
| :--- | :--- | :--- | :--- |
| **Lucifer** (Runtime) | `gemma-4-E4B-it-qat-UD-Q4_K_XL` | Q4_K_XL (Unsloth **post-fine-tune** QAT) | 666 |
| **Obi** (Observer) | `HERETICODER-2.5-3B-IT.i1-Q6_K` | Q6_K | 999 |

> **Important note on `gemma-4-E4B-it-UD-Q4_K_XL`:** the `UD` suffix in the
> model name denotes that this artifact has been **post-fine-tuned** before
> Unsloth's quantization-aware training pass. The base Gemma-4-E4B-it was
> adapted to task-specific data, *then* compressed to Q4_K_XL with QAT.
> This is not the same as the stock `gemma-4-E4B-it-Q4_K_XL` (QAT only,
> no post-FT). When specifying the model in `config.py`, `llama-server`
> launch commands, or evaluation scripts, use the post-FT variant
> explicitly — the runtime's behavior differs from the un-fine-tuned
> quantized base.

## What the empirical log (`logs/duellog.json`, 2026-07-23 to 2026-08-15)

| Model string as logged | Event count | Role as logged |
| :--- | :--- | :--- |
| `gemma-4-E4B-it-qat-UD-Q4_K_XL` | 46 | lucifer (canonical) |
| `gemma4-12B-it-qat` | 44 | lucifer (not documented in README) |
| `HERETICODER-2.5-3B-IT` | 36 | obi |
| `HERETICODER-2.5-3B-IT.Q8_0.gguf` | 25 | obi |
| `HERETICODER-2.5-3B-IT.Q8_0` | 2 | obi |
| `sample` | 1 | lucifer (synthetic placeholder) |

## Findings

1. **Two Lucifer models were used during the empirical window.** The
   README specifies `Gemma-4-E4B-it-UD-Q4_K_XL`. The log also contains
   44 events from `gemma4-12B-it-qat`. Either:
   - (A) An undocumented A/B test was performed; or
   - (B) The model was swapped at some point without updating the README.

   Either way, **any empirical claim that pools both model outputs is
   under-specified**. Future reports should split results by model or
   restrict to one.

2. **The `sample` row is synthetic.** Turn 0 contains a row with
   `text = "(no real run yet; this is a sample row)"`. Filter this from
   any empirical analysis.

3. **Obi's name had variant quantization strings** (`HERETICODER-2.5-3B-IT`,
   `HERETICODER-2.5-3B-IT.Q8_0`, `HERETICODER-2.5-3B-IT.Q8_0.gguf`). These
   refer to the same model but the string drift suggests the runtime accepts
   the filename verbatim from the model loader. Cosmetic, but worth
   normalizing.

## Recommended fixes (not yet applied)

- **Lock `config.py` to a single canonical Lucifer model** and assert at
  runtime that the loaded model string matches. Reject or warn otherwise.
- **Add a `tests/test_model_canonical.py`** that fails if the runtime
  reports a non-canonical model in the meta field.
- **Update `README.md` §III and §VII** with the precise spelling
  (`gemma-4-E4B-it-UD-Q4_K_XL`, hyphenated, lowercase, `.gguf` suffix
  excluded) so copy-paste into the launch command does not silently
  load a different quantization. Note that `UD` is meaningful — it
  denotes post-fine-tune, not just QAT; do not strip it.

## Status

- Filed as part of the Phase 1 hardening backlog.
- Tracked in `docs/decisions.md` roadmap indirectly (Phase 1 § "Implement
  strict output containment buffering").
- Not blocking publication — the kernel works with either Lucifer model
  on the empirical data we have, but the documentation should not
  pretend it only ever runs one.

## Updated provenance (2026-08-24)

Per the Architect, the canonical `gemma-4-E4B-it-UD-Q4_K_XL` is a
**post-fine-tuned** Gemma-4-E4B-it, not the stock QAT-only variant.
This affects:

- Reproducibility — anyone re-training or evaluating must use the
  same post-FT artifact, not the base QAT.
- Empirical claims — behavior observed against `gemma-4-E4B-it-UD-Q4_K_XL`
  is specific to that fine-tune; it does not transfer to the stock
  QAT-only model.
- Documentation — the `UD` suffix must be preserved in every reference,
  not normalized away.

## Status

- Filed as part of the Phase 1 hardening backlog.
- Tracked in `docs/decisions.md` roadmap indirectly (Phase 1 § "Implement
  strict output containment buffering").
- Not blocking publication — the kernel works with either Lucifer model
  on the empirical data we have, but the documentation should not
  pretend it only ever runs one.
