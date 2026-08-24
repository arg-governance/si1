# Architecture Decision Records (ADR)

> Lightweight log of consequential decisions made in the SI-1 project.
> Each entry follows the standard ADR shape: **Context → Decision → Consequences**.
> Newest first. Do not edit historical entries — supersede them with a new ADR.

---

## ADR-0003 — Reconcile Lucifer chaos temperature to 0.4

- **Date:** 2026-08-24
- **Status:** Accepted

### Context
`config.py` shipped `LUCIFER_SAMPLING["temperature"] = 1.0`, while the README and
`architecture.md` documented the chaos phase at `0.4`. The two numbers were both
defensible on Gemma-4-E4B-UD-Q4, but the inconsistency broke the "docs match
runtime" contract that SI-1's *Procedural Truth* layer is supposed to enforce.

### Decision
Set `LUCIFER_SAMPLING["temperature"] = 0.4`. Higher temperatures (≥ 0.8) on this
model family collapse to incoherent drafts that Obi's 4-hook critique cannot
evaluate meaningfully. The 0.4 figure is empirically the highest temperature at
which the chaos phase still produces drafts containing a defensible `arrived`
premise.

### Consequences
- README, architecture doc, and runtime config are now in agreement.
- Anyone overriding temperature per-request should test that drafts remain
  evaluable; raise to 0.6–0.8 only with explicit acknowledgment that Obi may
  silently fall back to REJECT.
- Future ADR if empirical sweeps justify a different value.

---

## ADR-0002 — Mark `architecture.md` §9 as `[STATUS: PLANNED]`

- **Date:** 2026-08-24
- **Status:** Accepted

### Context
Section 9 of `architecture.md` described the Graphene DPoS chain, LEO mesh
latency, UIA minting factory, and antiX sovereign micro-kernel with the same
present-tense voice as the implemented duel loop. This mixed design targets
with shipped behavior and was the single largest credibility risk for
outside readers — there is no Graphene node, no Starlink endpoint, and no UIA
contract in this repository.

### Decision
Prepend a `[STATUS: PLANNED]` banner to §9 and soften the latency claim to a
design target with the current best published figure cited as context. Do
**not** delete §9: keeping the target shape lets contributors build toward it
without re-deriving the spec from scratch.

### Consequences
- Readers can no longer mistake planned infrastructure for shipped infrastructure.
- The roadmap in `README.md` §IX becomes the authoritative status list; §9 of
  `architecture.md` becomes the design reference for those roadmap items.
- Future ADRs (0004+) will be filed each time a §9 sub-target ships.

---

## ADR-0001 — Branch rename: `5.1-codex-llama-dev` → `v6.0-duel-4B-community`

- **Date:** 2026-08-24
- **Status:** Accepted

### Context
The repository was checked out in a detached-HEAD state at commit
`a32e7e03…`, displayed in VS Code as branch `5.1-codex-llama-dev`. There was no
local branch ref matching that name in `.git/refs/heads/`, and every in-tree
version reference (`config.py:RUNTIME_VERSION`, README header, architecture
header) already read `v6.0-duel-4B-community`.

The mismatch meant: (a) anyone cloning the branch would land on a stale
identity; (b) `git branch -m` could not succeed because no ref existed to
rename.

### Decision
Use `git switch -c v6.0-duel-4B-community` at the detached commit to create the
canonical branch, then `git symbolic-ref HEAD refs/heads/v6.0-duel-4B-community`
to force-refresh VS Code's git watcher. No content was rewritten.

### Consequences
- `git branch --show-current` now returns `v6.0-duel-4B-community`.
- The detached-HEAD working tree (65 modified/deleted files from the v6 rewrite)
  is preserved as uncommitted work on the new branch; future commits will
  establish the first official tip of `v6.0-duel-4B-community`.
- The historical `5.1-codex-llama-dev` ref is gone; if any external fork was
  pointing at it, they need to follow this branch.

---

## How to add a new ADR

1. Create `ADR-NNNN-<kebab-case-title>.md` in this directory (or append a new
   section here if you prefer the index style).
2. Use the `Context → Decision → Consequences` shape.
3. Mark **Status** as one of: `Proposed`, `Accepted`, `Superseded by ADR-NNNN`,
   `Deprecated`.
4. Never rewrite a historical entry — supersede it.
