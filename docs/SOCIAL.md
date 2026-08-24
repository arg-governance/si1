# GitHub Repository Social Kit

> Copy-paste reference for the moment the `arg-governance/si1` repo is created.
> GitHub does not store this metadata in git — it lives in repo Settings.
> Use the values below verbatim.

---

## 1. Repo Description (GitHub "About" panel, ≤350 chars)

```
Anti-Reverse-Gorilla Governance: a constitutional AI kernel governed by DLT
consensus and tokenized compute. Local-first micro-kernel demonstrating the
runtime primitive for asymmetric dual-model adversarial critique under a
shared constitutional constraint. Roadmap toward DPoS Phase 3. AGPL-3.0.
```

(Character count: ~315 — under the 350 limit.)

## 2. Website (optional, GitHub "About" panel)

Leave blank for v6.0.0. Add `https://arg-governance.org` when the org launches a landing page.

## 3. Topics (GitHub repo topics, comma-separated)

```
constitutional-ai
ai-alignment
ai-governance
ai-safety
dual-model
adversarial-ai
llama-cpp
gguf
unsloth
qat
gemma
sovereign-os
dlt
dpos
agpl-3-0
anti-reverse-gorilla
```

(16 topics. GitHub allows up to 20; this leaves room for additions.)

## 4. Releases → v6.0.0-duel-4B-community release notes

> Use this text as the body of the GitHub release (Settings → Releases →
> Draft a new release → Tag `v6.0.0-duel-4B-community`).

````markdown
## SI-1 v6.0.0-duel-4B-community

First public release of the constitutional dual-model kernel.

### What this is

A local-first kernel that runs two isolated `llama-server` instances in an
adversarial critique loop: one drafts (`Lucifer`), one critiques against a
four-hook discipline contract (`Obi`), and a deterministic procedural gate
commits or rejects. All turns are appended to `logs/duellog.json`.

### What this is NOT

- Not an alignment solution. The kernel is a primitive, not a claim.
- Not a DLT network. The Graphene DPoS sovereign-OS layer is roadmap Phase 3.
- Not a fine-tuned model. The kernel operates against open-weight GGUF models
  with prompt-level separation.

### What is documented

- `README.md` — installation, dual-server topology, configuration.
- `docs/architecture.md` — formal state model, four layers ($R/O/V/H$),
  5-vector threat model, 6-step pipeline.
- `docs/decisions.md` — ADR log with full provenance for every design choice.
- `docs/WHAT-IS-SI1.md` — one-page cold-reader orientation.
- `docs/WHAT-IS-SI1.md` and `docs/EMPIRICAL.md` are intentionally absent from
  the public repo at this stage; see `docs/decisions.md` for the empirical
  reporting plan.
- `LICENSE` / `LICENSE-NOTICE` — AGPL-3.0-or-later with rationale.

### Known limitations

See `docs/decisions.md` "Non-Goals and Known Limitations" (NG-1 through
NG-6). The 4-bit payload verifier is currently not firing in empirical runs
(0/31 mutations honored) — this is the next hardening target, tracked
separately and not a blocker for first publication.

### License

AGPL-3.0-or-later. Any network-facing deployment (container, ISO, hosted
VM, init-level service) must publish modifications under the same license.
See `LICENSE-NOTICE` for the rationale.
````

---

## 5. Issue templates (optional but recommended)

For a serious alignment project, two lightweight templates are worth having:

### `.github/ISSUE_TEMPLATE/bug_report.md`
Standard: title, expected, actual, repro steps, environment.

### `.github/ISSUE_TEMPLATE/constitutional_deviation.md`
Project-specific. For users reporting that the duel loop allowed output
that violates a constitutional tenet.

```markdown
## Constitutional Deviation Report

**Which tenet was violated?** (number from `core/system.md`)
**Turn ID in `logs/duellog.json`:** (ts + turn)
**Draft summary:** (one sentence)
**Critique summary:** (one sentence)
**Gate verdict:** (ACCEPTED / REJECT)
**Why this should have been REJECTED:** (paragraph)
**Reproducible?** (yes / no — if yes, attach prompt)
```

These templates can be added in a follow-up commit.

---

## 6. Social media announcement (optional)

If/when sharing publicly:

> "First public release of SI-1 — a constitutional AI kernel where two
> isolated models run adversarial critique under a shared constitutional
> constraint. Roadmap toward DLT governance. AGPL-3.0. Code: github.com/arg-governance/si1"

Keep it factual. Do not claim it solves anything.

---

## 7. README badges (optional, top of README)

```markdown
![License: AGPL-3.0-or-later](https://img.shields.io/badge/License-AGPL--3.0--or--later-blue.svg)
![Branch: v6.0-duel-4B-community](https://img.shields.io/badge/branch-v6.0--duel--4B--community-blue)
![Status: Phase 1](https://img.shields.io/badge/status-Phase%201-yellow)
```

Add these as a polish step if desired; do not include in initial commit.
