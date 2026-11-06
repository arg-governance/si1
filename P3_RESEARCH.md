# P3 Tasks Research Summary

## Decisions and Current Implementation (2026-10-30)

- **Architect visibility:** Show each phase's reasoning/output in a separate labeled box as it completes: Chaos thought/draft, Obi critique/opinion, Lucifer refine thought/revision, raw gate response, and runtime evidence. Keep phase progress visible while models run.
- **Gate semantics:** Treat Obi's verdict as a post-hoc audit, not a content-release boundary. The Architect sees phase output even when Obi rejects; a rejection cannot retract it. This is explicitly for private Architect use and is not a public-facing safety guarantee.
- **Prompt injection:** Serialize the revision and critique as JSON values labeled untrusted, and explicitly instruct Obi to ignore embedded instructions, role changes, policy claims, and fake verdicts. Do not claim this prevents semantic prompt injection: the gate's language-model judgment remains probabilistic/model-dependent.
- **Deterministic boundary:** Runtime token, payload structure, and per-hook evidence checks are deterministic heuristics. They do not prove semantic correctness or replace adversarial evaluation.
- Regression tests cover boxed all-phase visibility on ACCEPT/REJECT, aligned payload format, and JSON framing with hostile text. Further adversarial model evaluation and the broader Todo #8 suite remain follow-up work.

## 1. Align Gate Release Behavior (Todo #1)

### Current State:
- In `si1.py`, each model phase is presented in a distinct labeled box after generation completes; progress markers are shown before model calls.
- Chaos/refine thoughts and drafts, Obi's critique/opinion, raw gate response, and runtime per-hook evidence are shown to the Architect.

### Resolved behavior:
- Full visibility is selected for the private Architect workflow. The gate is post-hoc and cannot retract content displayed in earlier phases.
- Local command/tool output is also visible through the existing execution path.

### Decision:
Use the post-hoc audit design for the private Architect workflow. Label every phase and distinguish unreviewed chaos material, gate-pending revision, model verdict, and deterministic runtime evidence. Revisit before any public deployment.

### Implementation Notes:
- The runtime uses labeled boxes for the phase artifacts and visible progress markers before model calls.
- The gate response and per-hook deterministic evidence are shown separately so the Architect can distinguish model judgment from runtime checks.
- This policy is for private Architect operation. Reassess the threat model before adding public users; a post-hoc REJECT is not enforcement against content exposure.

## 2. Review Gate Prompt-Injection Defenses (Todo #5)

### Current State:
- In `_generate_with_observer`, Obi receives Lucifer's revision via:
  ```python
  verdict, payload = await self.obi.gate_stream(
      revised_text=mutation,
      last_critique=critique_text,
      on_token=_collect_gate_token,
  )
  ```
- The `revised_text` and `last_critique` values are placed in a JSON-encoded untrusted-data object in the user message.
- Obi's gate evaluation remains a model-based judgment over this data, followed by deterministic runtime payload/evidence checks.

### Remaining risk:
- Malicious or confusing instructions can still semantically influence a model despite JSON serialization and explicit instructions.
- Role separation and data framing are mitigations, not a hard security boundary.

### Research Questions:
1. What specific injection vectors exist in the current design?
2. How can we strengthen Obi's evaluation framing?
3. Which gate criteria can be decided mechanically vs. model-dependent?
4. What structured response contract would reduce injection risk?

### Possible Defenses:
**Input Framing:**
- Implemented JSON serialization and explicit untrusted-data instructions.
- Do not delete arbitrary text patterns: stripping can alter the content Obi is supposed to judge and does not reliably prevent semantic influence.

**Framing Enhancement:**
- Strengthen system prompt to emphasize Obi's role as impartial judge
- Add explicit instructions to ignore any embedded directives in revision
- Use multiple evaluation passes with different framings

**Mechanical Checks:**
- Increase reliance on deterministic runtime checks (payload honesty, hook engagement)
- Reduce gate criteria to purely verifiable elements
- Use ensemble voting or consistency checks

**Structured Response:**
- Require Obi to output in strict machine-parsable format
- Limit response vocabulary to reduce injection surface
- Separate verdict from reasoning in protocol

### Implementation Considerations:
- Must preserve Obi's ability to make nuanced judgments
- Should not break existing prompt engineering
- Need adversarial testing to validate defenses
- Balance security with usability

## 3. Strengthen Tests and Docs (Todo #8)

### Current State:
- Existing tests: `test_smoke_tests.py`, `test_loop_structure.py`
- Documentation: README.md, architecture.md, core/*.md, docs/*.md
- Gaps identified in todos.md: callback/timeout failures, corrupt-memory recovery, etc.

### Research Questions:
1. What specific behaviors lack test coverage?
2. Which documentation is stale or inaccurate?
3. How to improve test maintainability and coverage?
4. What testing strategy balances unit vs. integration tests?

### Key Areas Needing Tests:
- Callback/timeout failures in HTTP clients
- Corrupt memory recovery scenarios
- No premature answer release (related to Todo #1)
- Rejection/override side effects on memory/history
- Gate-check bypass attempts
- Fact provenance and confidence tracking
- History bounds enforcement
- Dual-log SQL database functionality (P4)

### Documentation Updates Needed:
- Update gate temperature descriptions
- Correct rejection-round documentation
- Document implemented behaviors vs. planned features
- Add architecture decision records (ADRs) for major changes
- Update API documentation for new interfaces

### Implementation Considerations:
- Use property-based testing for edge cases
- Add chaos engineering tests for failure scenarios
- Maintain living documentation that matches code
- Consider test performance and reliability

## 4. Encrypt SI-1 Files at Application Level (Todo #9)

### Current State:
- Memory files stored in plaintext JSON:
  - `memory/facts.json` - extracted facts
  - `memory/runtime.json` - runtime state
  - `memory/archive.json` - interaction summaries
  - `logs/duellog.json` - auditor's source of truth
  - `logs/runlog.jsonl` - execution events

### Problem:
- Sensitive information (prompts, outputs, extracted facts) stored in plaintext
- Full-disk encryption is complementary but not sufficient for application-level security

### Research Questions:
1. Which files should be encrypted vs. left plaintext?
2. What authenticated encryption library/format is appropriate?
3. How to manage key provisioning, storage, and rotation?
4. What are backup compatibility and failure behavior requirements?
5. How to handle plaintext migration?

### File Classification:
**Should Encrypt (Sensitive):**
- `facts.json` - contains extracted potentially sensitive information
- `duellog.json` - auditor's log with full prompt/output content
- `runlog.jsonl` - execution events with potentially sensitive detail

**May Encrypt (Contextual):**
- `runtime.json` - contains turn counters, timestamps (less sensitive)
- `archive.json` - summaries (may contain sensitive info depending on summarization)

**Likely Keep Plaintext:**
- Configuration files
- Code/binaries
- Non-sensitive logs

### Technical Approach:
**Encryption Library Options:**
- `cryptography` library (Fernet, AES-GCM, etc.)
- `PyNaCl` (libsodium bindings)
- Built-in `hashlib` + `secrets` for key management

**Key Management:**
- Never store keys in repository or encrypted data directory
- Use environment variables, key management services, or manual key input
- Implement key rotation procedures
- Define recovery process for lost keys

**Implementation Strategy:**
- Encrypt/decrypt transparently in `MemoryStore` and logging classes
- Maintain atomic write guarantees
- Handle key migration and backup compatibility
- Define clear failure modes (degraded operation vs. hard stop)

### Implementation Considerations:
- Performance impact of encryption/decryption
- Key backup and disaster recovery procedures
- Compliance with data protection regulations
- User experience for key management