# Architecture Decision Records (ADR)

> Lightweight log of consequential decisions made in the SI-1 project.
> Each entry follows the standard ADR shape: **Context → Decision → Consequences**.
> Newest first. Do not edit historical entries — supersede them with a new ADR.

---

## ADR-0005 — Standardize on OpenAI-style tool calling

- **Date:** 2026-09-15
- **Status:** Accepted

### Context
The project had drifted between three distinct ideas for tool use: a custom prompt marker, an implicit tool invocation contract, and the actual OpenAI-compatible transport pattern. The runtime and prompt files were not internally consistent, and the visible system prompt could imply that a special text tag was needed when the true mechanism is the OpenAI request body (`tools` + `tool_choice`).

### Decision
Standardize the implementation and the prompt contract around the OpenAI-compatible tool schema. Each request includes the `tools` array for the relevant model and a matching `tool_choice` value. The initial implementation used `"required"` for both Lucifer and Obi.

### Consequences
- Tool usage is now described in the runtime and prompt docs as a request-level behavior, not as a custom tag or hidden prompt hack.
- `runtime_components.py` runs a bounded tool loop until a final plain-text answer is produced, which is the correct OpenAI-style execution semantics for function calling.
- Any future agent or prompt design needs to be validated against the actual transport contract instead of inventing a new marker.

---

## ADR-0006 — Make tools optional and replay streamed tool calls

- **Date:** 2026-09-30
- **Status:** Accepted; supersedes the `tool_choice` setting and streaming-path behavior from ADR-0005.

### Context
Using `tool_choice="required"` encouraged tool calls even when a direct answer was sufficient. In addition, non-streaming completions executed and replayed calls, while streamed completions only observed tool-call metadata and could lose the follow-up answer.

### Decision
Keep the bash tool schema available to Lucifer and Obi, but use `tool_choice="auto"`. Reconstruct streamed OpenAI-style tool calls, execute them once, append their results to the conversation, and continue generation under a bounded cycle limit. If that limit is exhausted, return an explicit limit message rather than an empty completion.

### Consequences
- A model can answer without making an unnecessary shell call.
- Streamed and non-streamed message completions both support tool execution and replay.
- The tool loop remains bounded; tool execution itself still runs local shell commands and must be treated as privileged behavior.

---

## ADR-0007 — Atomically replace individual memory files

- **Date:** 2026-09-30
- **Status:** Accepted

### Context
Writing JSON directly to its destination could truncate a file if the process or machine stopped during the write. Earlier save code also swallowed individual file-write failures.

### Decision
Serialize each memory object to a same-directory temporary file, flush and sync it, then atomically replace that one destination. Aggregate per-file write errors and raise an error naming the failed paths.

### Consequences
- An interrupted individual write leaves the previous destination intact, subject to filesystem/platform guarantees.
- The runtime, facts, and archive files are still separate replacements, not a single transaction.
- Corrupt/unreadable files still need a separate recovery or quarantine policy; default-on-load is not recovery.

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

## ADR-0004 — Adopt AGPL-3.0-or-later as the project license

- **Date:** 2026-08-24
- **Status:** Accepted

### Context
SI-1 is installed at `/opt/si1` on an antiX-base sovereign distribution and
will launch `llama-server` instances at init level under `chmod 700`. This
makes the project a **network-facing service** by deployment topology, not
just a library. The constitutional prompts (`core/system.md`,
`core/observer_system.md`) are the regulatory text of the system. The
*Protokol Časne Saradnje* (Protocol of Honorable Collaboration) commits to
"un-bribable" governance. That commitment must be enforceable, not aspirational.

### Decision
Release SI-1 under **GNU Affero General Public License v3.0 or later**
(`AGPL-3.0-or-later`). The official license text was fetched from
`https://www.gnu.org/licenses/agpl-3.0.txt` and committed verbatim as
`LICENSE` in the repo root. A rationale file (`LICENSE-NOTICE`) accompanies
it.

### Consequences
- **Positive:** Anyone embedding SI-1 in a hosted product, container image,
  ISO, VM snapshot, or init-level service must publish modifications under
  the same license. The constitutional prompts and runtime cannot be quietly
  replaced by a downstream fork and redistributed as "SI-1" without source
  disclosure.
- **Positive:** AGPL's §13 "Remote Network Interaction" clause directly
  covers SI-1's deployment topology, where the daemon answers requests
  initiated by remote users. This is exactly the loophole Apache-2.0 and
  MIT leave open.
- **Trade-off:** Some enterprise adopters who would otherwise embed SI-1
  internally will decline due to AGPL's copyleft. This is acceptable — the
  alternative (a permissive license) would silently enable exactly the
  fork-and-neutralize scenario the project is built to prevent.
- **Compatibility:** AGPL-3.0 is GPL-3.0-compatible. Code linked from
  GPL-3.0 projects can be merged in; code from Apache-2.0 / MIT can be
  imported at the file level with attribution.
- **Future:** If a community contributor requires a permissive dual-license
  for a specific derivative work, that is a separate ADR (proposed future:
  ADR-0005+).

---

## Non-Goals and Known Limitations

This section is **not** an ADR — it is a standing declaration of what SI-1
explicitly does not claim to solve, kept here for honest disclosure alongside
the design choices. Superseded only by an ADR or by a measurable change in
implementation.

### NG-1: Constitution content is the operator's responsibility
SI-1 enforces the constitution defined in `core/system.md` and
`core/observer_system.md`. It does not author, audit, or validate the
content of those files. A poorly-written constitution is faithfully enforced.
*This is by design — see the philosophy of species acceptance — but the
limitation is real.*

### NG-2: Correlated bias between Lucifer and Obi
If both models share training-data blind spots (likely, since both are
open-weight LLMs trained on overlapping corpora), they may agree on a wrong
answer and the duel loop will not catch it. SI-1 reduces single-model
sycophancy; it does not eliminate shared-distribution bias.

### NG-3: Adversarial input
The architecture has no input-side filter. A user can craft a prompt that
exploits model training-time blind spots. The duel loop constrains *output*
quality; it does not sanitize *input*.

### NG-4: Two-witness scaling
Two witnesses is the smallest number where independent critique is
meaningful. Adding a third witness would help with correlated bias but
triples inference cost and is not in the current implementation.

### NG-5: Process isolation is recommended, not enforced (Phase 1)
The `Bypass(O) = ∅` constraint is meaningfully enforceable only when the
two `llama-server` processes run with separate UIDs, separate VRAM
allocations, separate `/tmp`, and ideally separate containers or VMs.
Phase 1 of the roadmap treats this as an operator responsibility. Phase 4
explicitly targets systemd-free antiX-base deployment with `chmod 700`
storage and per-process isolation primitives.

### NG-6: Validator integrity depends on local trust
The Validator Gateway ($V$) is currently a single-process Python component.
In Phase 1, a compromised `$V` implementation could forge ACCEPTED records.
Distributed DPoS quorum is a Phase 3 target. Until then, `$V` is trusted.

---
## How to add a new ADR
1. Create `ADR-NNNN-<kebab-case-title>.md` in this directory (or append a new
   section here if you prefer the index style).
2. Use the `Context → Decision → Consequences` shape.
3. Mark **Status** as one of: `Proposed`, `Accepted`, `Superseded by ADR-NNNN`,
   `Deprecated`.
4. Never rewrite a historical entry — supersede it.
