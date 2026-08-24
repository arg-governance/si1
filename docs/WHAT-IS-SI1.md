# What is SI-1?

> A one-page orientation for people who have never heard of this project.

---

## TL;DR

SI-1 is a small **local kernel** that runs two open-weight language models against
each other — one drafts an answer, the other critiques the draft against a fixed
set of constitutional rules — and only commits the result if both models agree.
Everything is logged, hashed, and auditable. Nothing leaves your machine.

It is *not* an assistant. It is the smallest piece of infrastructure that an
honest assistant would have to be built on top of.

---

## The three things you should remember

1. **Two models, one task.** A reasoning model ("Lucifer") generates a draft.
   A second model ("Obi") critiques it against four constitutional hooks
   (`arrived / overlooked / principle / reevaluate`) and either accepts or
   hard-drops the output. The two never share a KV-cache — Obi's evaluation
   is stateless by design.

2. **Procedural truth ≠ semantic truth.** SI-1 separates *whether the
   pipeline ran correctly* (cryptographic hashing, turn ordering, signature
   verification) from *whether the answer is correct* (epistemic critique).
   Each plane has its own guarantees and its own failure modes.

3. **The constitution is data, not vibes.** The "law" the runtime enforces is
   just two Markdown files ([`core/system.md`](../core/system.md) and
   [`core/observer_system.md`](../core/observer_system.md)). You can read
   them in five minutes. They can be amended — but only slowly, by a human,
   through a documented procedure.

---

## What SI-1 is not

| Not this | Why |
| :--- | :--- |
| A new foundation model | SI-1 is harness code around existing GGUF models (Gemma-4-E4B, Hereticoder-2.5-3b). It does not train or fine-tune weights at runtime. |
| A chatbot framework | There is no persona, no chat history sidebar, no plugin system. It is a kernel you call from a CLI. |
| A corporate alignment product | There is no safety classifier, no RLHF wrapper, no content moderation API. The critique happens *between* models, not *on top of* the output. |
| A decentralized network today | The Graphene DPoS chain, LEO mesh, and UIA mint factory described in [`architecture.md`](architecture.md) §9 are documented as **planned** design targets, not shipped infrastructure. |

---

## How big is the codebase?

About 2,000 lines of Python:

```
si1.py                  # 4-phase duel loop orchestrator
config.py               # endpoints, sampling, paths
runtime_components.py   # Generate(), ThoughtRouter, DuelLog
memory_store.py         # facts.json / runtime.json / archive.json
fact_extractor.py       # post-turn fact distillation
fact_validator.py       # constitutional coherence checks
prompt_engine.py        # ChatML compilation
logger.py               # structured JSONL output
models.py               # dataclasses for turns / events
```

Plus one browser-native HTML dashboard at [`web/dashboard.html`](../web/dashboard.html).

---

## Who is this for?

- **Researchers** studying adversarial / dual-model architectures who want a
  reproducible baseline smaller than a full RLHF pipeline.
- **Engineers** who want a local, offline, fully-logged reasoning loop they can
  audit with `grep` and `jq`.
- **Cynics of corporate AI safety** who want to see whether structural
  separation of concerns can be implemented at all without a billion-dollar
  compute budget.

If you want a polished chat product, this is not it. If you want a kernel you
can read end-to-end in an afternoon, it is.

---

## Where to go next

- **[README.md](../README.md)** — full installation and dual-server setup.
- **[docs/architecture.md](architecture.md)** — formal state model, layer
  functions, threat model, 6-step pipeline.
- **[docs/decisions.md](decisions.md)** — Architecture Decision Records (why
  the runtime is shaped the way it is).
- **[core/system.md](../core/system.md)** — the actual constitutional text
  the runtime enforces. Read this if you read nothing else.
