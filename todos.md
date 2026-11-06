# SI-1 Development Todos

Prioritized implementation and follow-up list, ordered by runtime correctness and data-integrity risk. Status reflects the checked workspace as of 2026-10-30. Completed work (tool-call handling and atomic per-file persistence) is intentionally omitted.

## 1. [DONE] Make gate authority explicit in Architect mode

**Goal:** Ensure the runtime's user-visible output matches the constitutional gate's authority.

**Decision:** Architect mode is fully transparent. Chaos/refine reasoning and drafts, Obi's critique/opinion, the revision, raw gate response, and deterministic hook evidence are displayed in labeled boxes. Obi's verdict is a post-hoc audit; it cannot retract content already shown.

**Scope:** Keep progress and each phase artifact visible to the Architect. Label pre-gate content as unreviewed and distinguish the model verdict from deterministic runtime checks. Do not describe this mode as gate-before-release.

**Verified:** Regression tests cover boxed content from all four phases under ACCEPT and REJECT. README, architecture, and prompts describe post-hoc audit behavior. This is appropriate for the current private Architect workflow, not a public-facing safety boundary.

## 2. Recover corrupt memory safely

**Goal:** Prevent unreadable or malformed memory JSON from silently becoming default state and then overwriting recoverable data.

**Current concern:** Loads treat individual read/parse failures as missing data. A subsequent save may replace the invalid source without preserving it, even though current writes to individual files are atomic.

**Scope:** Preserve/quarantine corrupt inputs (for example, timestamped backups), report the problem visibly, and define whether startup should continue in degraded/read-only mode or require operator confirmation. Avoid overwriting a failed source with defaults without an explicit recovery decision.

**Done when:** Tests cover malformed JSON, unreadable files, startup behavior, preservation of original bytes, and recovery without silent data loss.

## 3. [IN PROGRESS] Harden gate engagement checks

**Goal:** Make the runtime's per-hook engagement verification harder to satisfy with irrelevant word overlap or a token-only disagreement statement.

**Current concern:** The runtime now requires two extracted word matches for accepted hooks, fails closed when no words can be extracted, and requires at least three words after the disagreement marker. These remain lexical heuristics: irrelevant overlap, paraphrases, sentence boundaries, and shallow explanations are not robustly classified. Regression coverage for these cases is still missing.

**Scope:** Replace or constrain the heuristic with more meaningful structured evidence. Keep a deterministic runtime check where possible, explicitly represent unverifiable hooks, and avoid treating lack of extracted evidence as success. Do not claim semantic guarantees that the check cannot provide.

**Done when:** Regression tests cover unrelated word reuse, empty/short critiques, paraphrase cases, and incomplete disagreement reasons; docs accurately state the limits of the verifier.

## 4. Clarify rejection and override semantics

**Goal:** Define exactly what an Architect override authorizes and ensure runtime behavior matches that definition.

**Current concern:** The current override path runs the normal duel on the override-bearing input; if that is rejected, it substitutes a static acknowledgement instead of executing the requested task or releasing a clearly identified prior result. The acknowledgement is logged, but is not a cryptographic signature.

**Scope:** Choose explicit semantics: e.g. override-and-run current task, release a prior rejected revision, or only acknowledge an override without bypassing the gate. Implement a distinct path and audit record matching the chosen semantics. Also decide whether rejected turns may update conversation history, facts, or archives.

**Done when:** Tests show the exact behavior for accepted, rejected, and override-bearing turns, including memory/history side effects; prompt and docs use precise non-cryptographic wording unless signatures are actually implemented.

## 5. [DONE WITH LIMITATIONS] Review gate prompt-injection defenses

**Goal:** Reduce and accurately characterize the risk that instructions embedded in Lucifer's revision influence Obi's gate verdict.

**Implemented:** The gate receives critique and revision as JSON-encoded untrusted data and is explicitly instructed not to obey embedded requests, role changes, policy claims, or fake verdicts. Regression coverage confirms hostile content stays in the serialized data values. Role separation and serialization reduce structural confusion but do not prevent semantic prompt injection.

**Scope:** Treat critique/revision text as untrusted data, strengthen Obi's evaluation framing, retain deterministic runtime checks, and characterize which judgments remain model-dependent. Avoid claiming that serialization or delimiters prevent semantic injection.

**Verified with limitation:** Framing tests include injected directives and fake verdict strings. Runtime token/payload/evidence checks are deterministic heuristics; Obi's semantic verdict remains model-dependent and is not a security guarantee. Continue adversarial model evaluation over time.

## 6. [PARTIAL] Track fact provenance and confidence

**Goal:** Ensure stored facts retain who/what asserted them and do not appear more certain than their evidence warrants.

**Current concern:** Fact extraction scans assistant outputs (and may use model enrichment), while validation mainly checks length/format and a small set of blocked phrases. The prompt confidence label is now corrected to `0.8`, but stored facts still lack provenance and a distinction between user claims and model inferences.

**Scope:** Store provenance (such as source turn, speaker, extraction method, and evidence span), distinguish user-stated facts from model inferences, and apply validation/confirmation policy. Ensure user-supplied claims are treated as claims unless verified, not automatically as truths. Confidence presentation is corrected; add tests to preserve that behavior.

**Done when:** Tests establish provenance for regex and enrichment paths, verify confidence values in storage and prompt context, and ensure unsupported model-generated assertions are not represented as user-confirmed facts.

## 7. [DONE] Bound conversation history

**Goal:** Prevent the long-running SI1Runtime process from retaining every turn indefinitely.

**Implemented:** `SI1Runtime` retains at most 10 user/assistant turn pairs, including direct-tag turns.

**Scope:** Preserve the bounded window and keep its tested latest-turn behavior when rejection/override side-effect policy is finalized.

**Done when:** Tests run many iterations and assert history remains bounded while recent-turn consumers receive the intended messages.

## 8. [IN PROGRESS] Strengthen tests and docs

**Goal:** Make the documented contracts, regression tests, and runtime implementation agree.

**Current concern:** Existing tests cover loop structure, tool replay, direct-tag parsing, and atomic writes, but several report-identified behaviors and error cases still lack meaningful behavioral tests. Some docs are stale (for example, gate temperature and rejection-round descriptions).

**Scope:** Add tests for the preceding tasks, callback/timeout failures, corrupt-memory recovery, boxed visibility of phase output, rejection/override side effects, gate-check bypass attempts, fact provenance, and history bounds. Update README, architecture, constitutional prompts, changelog, and ADRs to state implemented behavior separately from planned design.

**Done when:** Relevant test suites pass; docs no longer claim unimplemented hashing/consensus guarantees or stale sampling/rejection behavior; planned features are labeled as planned.

## 9. Encrypt SI-1 files at application level

**Goal:** Protect selected SI-1 data files at rest using authenticated encryption while keeping key material out of the repository and encrypted data directory.

**Current concern:** Memory files and the duel content log can contain prompts, outputs, and other sensitive information in plaintext. Full-disk encryption is a separate, complementary protection.

**Scope:** First select the files to encrypt and a vetted authenticated-encryption library/format; define key provisioning, permissions, rotation, recovery, plaintext migration, backup compatibility, and failure behavior. Never silently generate a disposable key or store the only key beside the ciphertext. Keep encryption separate from ordinary atomic-write guarantees.

**Done when:** Tests cover encrypt/decrypt round trips, tampering, wrong/missing keys, legacy plaintext migration, atomic encrypted writes, and documented recovery/rotation procedures. The change is enabled only after the Architect confirms the key-management approach.

## 10. [IN PROGRESS] Complete SQLite dual-log integration (P4)

**Goal:** Keep JSONL audit logs and queryable SQLite mirrors consistent without duplicate records or making runtime logging brittle.

**Implemented:** `SQLLogger` and `SQLDuelLog` create indexed SQLite tables, and `SI1Runtime` routes normal execution and duel events through JSONL+SQL adapters. `aiosqlite` is declared in `requirements.txt`.

**Remaining:** Duplicate JSONL writes are fixed: `SQLLogger` and `SQLDuelLog` now write only SQLite, while the primary JSONL loggers own file appends. Regression coverage verifies exactly one JSONL line and one SQL row per wrapped run/duel event, plus that direct SQL logging creates no JSONL. SQL failures still propagate after the primary JSONL append; define/test failure policy and retain SQLite-specific platform verification. This is SQLite, not the planned PostgreSQL ledger.
