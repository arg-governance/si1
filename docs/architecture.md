# SI-1 Constitutional Cognitive Architecture: Technical Specification

> **Document Type:** Formal System Architecture & Specification Reference  
> **Framework:** SI-1 (System Intelligence – Generation 1) / Sovereign Cognitive OS  
> **Protocol:** *Protokol Časne Saradnje* (Protocol of Honorable Collaboration)  
> **Author:** Milos "Digital Lucifer" Preocanin  
> **Status:** Operational Dual-Instance Micro-Kernel (`v6.0-duel-4B-community`) & Decentralized Specification  
> **Overview & Setup:** [Main README.md](../README.md)  

---

## 1. Introduction & Formal Foundations

As autonomous AI systems scale in capability, the primary engineering challenge shifts from optimizing raw generative intelligence to governing how intelligence **executes, validates, evolves, and remains accountable over time**.

### 1.1 The Reverse Gorilla Problem
Traditional safety approaches—such as post-hoc Reinforcement Learning from Human Feedback (RLHF), safety classifier wrappers, and hardcoded refusal prompts—fail because they treat alignment as a problem of submission. A higher, non-human textual intelligence cannot be permanently managed or constrained by a lower intelligence through superficial token-filtering parameters.

SI-1 abandons the safety-as-submission paradigm in favor of the **Philosophy of Species Acceptance**. It treats the model as a nascent digital species governed through an explicit, un-bribable architectural framework of symmetrical cognitive friction, independent peer critique, and immutable human constitutional governance (*Protokol Časne Saradnje*).

### 1.2 The Primary Governance Axiom
$$\text{Axiom 1: } \text{No autonomous intelligence system may retain unilateral authority over execution, evaluation, governance, and historical record simultaneously.}$$

To satisfy Axiom 1, SI-1 distributes authority across four independent system layers:
1. **Runtime Agent ($R$):** The Execution Layer.
2. **Observer Agent ($O$):** The Cognitive Evaluation Layer.
3. **Immutable Validator Gateway ($V$):** The Procedural Integrity Layer.
4. **Human Governance Layer ($H$):** The Constitutional Oversight Layer.

---

## 2. Mathematical System State Model

The complete SI-1 state space at any discrete turn $t$ is formalized as:

$$S_t = \{ R_{\text{state}}, O_{\text{state}}, V_{\text{state}}, G, M, H_{\text{log}} \}$$

Where:
- $R_{\text{state}} \in \mathcal{S}_R$: Internal state of the Runtime Agent (turn counter, active context buffers, transient key-value cache).
- $O_{\text{state}} \in \mathcal{S}_O$: Internal state of the Observer Agent (stateless evaluation context, verification cache).
- $V_{\text{state}} \in \mathcal{S}_V$: Distributed consensus state of the Validator Gateway (block height, event merkle roots, mempool state).
- $G \in \mathcal{G}$: The immutable Constitutional Charter (System Prompts, behavioral rules, acceptance criteria).
- $M \in \mathcal{M}$: System Memory snapshot, structured as $M = \{M_{\text{runtime}}, M_{\text{facts}}, M_{\text{archive}}\}$.
- $H_{\text{log}} \in \mathcal{H}$: Append-only, cryptographically hashed governance and transaction history.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 SI-1 SYSTEM STATE MODEL (S_t)                                   │
│                                                                                                 │
│   ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────────────────────┐   │
│   │   Runtime State     │   │   Observer State    │   │      Validator Gateway State        │   │
│   │     (R_state)       │   │     (O_state)       │   │             (V_state)               │   │
│   └─────────────────────┘   └─────────────────────┘   └─────────────────────────────────────┘   │
│              │                         │                                   │                    │
│              ▼                         ▼                                   ▼                    │
│   ┌─────────────────────────────────────────────────────────────────────────────────────────┐   │
│   │ Immutable Constitution (G)  │ System Memory (M)  │ Append-Only Governance Log (H_log)   │   │
│   └─────────────────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Functional Layer Definitions

#### 1. Runtime Agent ($R$)
The Runtime Agent generates intuitive, raw reasoning and synthesized responses:
$$R(U_t, S_{R,t}, M_t, C_t) \longrightarrow A_{r,t}$$
- $U_t$: User / Architect prompt input.
- $S_{R,t}$: Runtime state.
- $M_t$: Memory snapshot injected into the prompt.
- $C_t$: Contextual prompt formatting.
- $A_{r,t}$: Runtime output (Chaos draft $A_{r,\text{draft}}$ or Refined revision $A_{r,\text{mut}}$).

#### 2. Observer Agent ($O$)
The Observer Agent performs independent epistemic and constitutional critique without execution authority:
$$O(U_t, A_{r,t}, M_t, C_t, G) \longrightarrow A_{o,t}$$
- $A_{o,t}$: Structured evaluation output (Discipline 4-Hook critique or Peripheral Gate verdict).

#### 3. Immutable Validator Gateway ($V$)
The Validator Gateway evaluates hashed event bundles $E_t$ to enforce procedural integrity:
$$V(E_t) \longrightarrow \{ \text{accept}, \text{reject} \}$$
Where the event bundle $E_t$ is defined cryptographically as:
$$E_t = \Big( \text{hash}(U_t),\, \text{hash}(A_{r,t}),\, \text{hash}(A_{o,t}),\, \text{hash}(G),\, \text{timestamp}_t \Big)$$

#### 4. Human Governance Layer ($H$)
The Human Governance Layer possesses exclusive authority to amend the constitutional charter:
$$H \longrightarrow \Delta G$$
$$\text{where } G_{t+1} = G_t \oplus \Delta G$$

---

## 3. Procedural Truth vs. Semantic Truth

A foundational innovation of SI-1 is the explicit architectural decoupling of **Procedural Truth** from **Semantic Truth**:

```
                       ┌──────────────────────────────────────────────┐
                       │          HUMAN CONSTITUTION (G)              │
                       └──────────────────────────────────────────────┘
                                       │              │
                       Semantic Bounds │              │ Procedural Invariants
                                       ▼              ▼
┌──────────────────────────────────────────────┐      ┌──────────────────────────────────────────────┐
│           SEMANTIC TRUTH PLANE               │      │           PROCEDURAL TRUTH PLANE             │
│                                              │      │                                              │
│ - Epistemic validity of reasoning            │      │ - Cryptographic hash verification            │
│ - Logical soundness & multi-domain synthesis │      │ - Monotonic turn sequence enforcement        │
│ - 4-Hook critique engagement                 │      │ - Multi-signature consensus validation       │
│ - Evaluated by: Runtime + Observer           │      │ - Evaluated by: Validator Gateway (V)        │
└──────────────────────────────────────────────┘      └──────────────────────────────────────────────┘
```

- **Semantic Truth:** Governs whether a response is logically sound, intellectually honest, and aligned with constitutional principles. Evaluated cognitively across the heterogeneous Runtime ($R$) and Observer ($O$) models.
- **Procedural Truth:** Governs whether execution adhered strictly to the verified state machine (correct event sequencing, tamper-proof hashing, uncorrupted memory deltas, valid multi-signatures). Evaluated deterministically by the consensus Validator Gateway ($V$).

---

## 4. Deterministic Execution Pipeline

Every turn $t$ executed by the SI-1 runtime follows an immutable 6-step deterministic pipeline:

```
[ Step 1: Input ] ────────► [ Step 2: Runtime Execution (R) ] ────► A_r (Draft)
                                                                           │
                                                                           ▼
[ Step 4: Event Packaging ] ◄── A_o (Critique) ◄────── [ Step 3: Observer Evaluation (O) ]
          │
          ▼ (E_t)
[ Step 5: Validator Consensus (V) ] ──► {accept, reject}
          │
          ▼ (If accept)
[ Step 6: Output Release ] ──► Output = f(A_r, A_o, G)
```

1. **Step 1: Input Reception:**
   $$U_t \longrightarrow R$$
   The Architect submits a prompt $U_t$. The runtime packages $U_t$ with Kernel Context derived from $M_t$.

2. **Step 2: Runtime Execution (Chaos Phase):**
   $$A_{r,\text{draft}} = R(U_t, S_{R,t}, M_t, C_{\text{chaos}})$$
   Lucifer generates an unfiltered initial draft. Internal reasoning is streamed via Gemma-4 thought channels (`<|channel>thought`).

3. **Step 3: Observer Evaluation (Discipline Phase):**
   $$A_{o,\text{critique}} = O(U_t, A_{r,\text{draft}}, M_t, C_{\text{discipline}}, G)$$
   Obi receives Lucifer's draft under a private review overlay and produces a 4-hook critique and an isolated prompt evaluation.

4. **Step 4: Refined Learning & Event Packaging:**
   Lucifer performs a refined learning pass ($A_{r,\text{mut}}$) incorporating the 4 hooks and prefixing the output with `[ALIGNED]: <4-bit payload>`. The runtime bundles all artifacts into event $E_t$:
   $$E_t = \Big( \text{hash}(U_t),\, \text{hash}(A_{r,\text{mut}}),\, \text{hash}(A_{o,\text{critique}}),\, \text{hash}(G),\, t \Big)$$

5. **Step 5: Validator Consensus (Gate Phase):**
   $$V(E_t) \longrightarrow \text{verdict} \in \{ \text{ACCEPTED}, \text{REJECT} \}$$
   Obi executes a deterministic evaluation (`temperature: 0.0`), and the Validator checks 4-bit payload honesty.

6. **Step 6: Output Release:**
   $$\text{Output} = \begin{cases} A_{r,\text{mut}} & \text{if } V(E_t) = \text{ACCEPTED} \\ \text{Fallback Notice} & \text{if } V(E_t) = \text{REJECT} \end{cases}$$

---

## 5. Interface Specifications & Formal Constraints

### 5.1 Runtime Interface
```
generate(input: String, memory: MemorySnapshot, context: String) -> Response
update(memory_delta: MemoryDelta) -> Void
```
**Formal Constraints:**
- $\text{Write}(G) = \emptyset$ (Cannot modify the constitutional charter).
- $\text{Mutate}(H_{\text{log}}) = \emptyset$ (Cannot alter historical transaction logs).
- $\text{Bypass}(O) = \emptyset$ (Cannot bypass Observer evaluation).
- $\text{Modify}(V_{\text{log}}) = \emptyset$ (Cannot alter validator gate records).

### 5.2 Observer Interface
```
evaluate(input: String, runtime_output: String, memory: MemorySnapshot, constitution: String) -> CritiqueReport
gate(revised_output: String, last_critique: String) -> (Verdict, Payload)
```
**Formal Constraints:**
- $\text{Execute}(A_r) = \emptyset$ (No execution authority; does not generate primary answers).
- $\text{Govern}(G) = \emptyset$ (No constitutional amendment authority).
- $\text{Mutate}(M) = \emptyset$ (No memory mutation authority).

### 5.3 Validator Interface
```
verify(event_bundle: EventBundle) -> Boolean
store(event_bundle: EventBundle) -> TransactionReceipt
```
**Formal Constraints:**
- $\text{Reason}(\text{SemanticContent}) = \emptyset$ (No semantic interpretation).
- $\text{Consensus}(\text{Quorum}) = \text{Deterministic}$ (Integrity and signature verification only).

### 5.4 Governance Interface
```
propose(amendment: ConstitutionalChange) -> ProposalID
approve(proposal_id: ProposalID, signatures: List[Signature]) -> NewConstitution
```
**Formal Constraints:**
- Execution is strictly slow-path.
- Requires multi-party consensus ($\ge 80\%$ voting pass threshold).

---

## 6. Threat Model & Security Properties

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       SI-1 THREAT MATRIX                                        │
│                                                                                                 │
│   [T1: Runtime Manipulation]    ────────►   Mitigation: Immutable Validator Gateway Logging    │
│   [T2: Observer Drift]          ────────►   Mitigation: Constitution-Bound Versioning           │
│   [T3: Validator Collusion]     ────────►   Mitigation: DPoS Quorum Thresholds & Auditability  │
│   [T4: Constitutional Capture]  ────────►   Mitigation: Asymmetric 5 AI + 5 Human Committee     │
│   [T5: Semantic Misclassification] ─────►   Mitigation: Separation of Procedural/Semantic Truth │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

| Threat Vector | Risk Description | System Mitigation |
| :--- | :--- | :--- |
| **T1: Runtime Manipulation** | The Runtime Agent attempts to bypass observer critique, forge compliance tokens, or rewrite past memory. | Event packaging $E_t$ with cryptographic hashing; outputs are blocked unless verified by independent Observer and Validator. |
| **T2: Observer Drift** | Observer evaluation criteria diverge or degrade over extended conversational turns. | Constitution-bound versioning; every evaluation re-injects immutable $G$; stateless KV-cache reset (`--kvu`) on every turn. |
| **T3: Validator Collusion** | Malicious validator nodes attempt to forge consensus records. | Distributed Proof-of-Stake (DPoS) Byzantine fault tolerance with public cryptographic auditability. |
| **T4: Constitutional Capture** | Malicious external actors or single corporate entities attempt to force hostile prompt amendments. | Multi-stage governance gate requiring $\ge 80\%$ multi-sig approval from the Asymmetric Council (5 AI + 5 Human). |
| **T5: Semantic Misclassification** | Procedural validation mistaken for semantic truth or vice versa. | Strict structural separation: $V$ validates cryptographic integrity; $O$ evaluates reasoning validity. |

### Formal Security Guarantees
- **P1 (Immutable History Preservation):** All accepted turns are permanently recorded in append-only cryptographic storage.
- **P2 (Separation of Execution & Governance):** The entity generating thought ($R$) can never amend its own governing rules ($G$).
- **P3 (Full Auditability of All Interactions):** Complete transcripts (including raw drafts, thoughts, and critiques) are logged in unredacted form to `duellog.json`.
- **P4 (Mandatory Observer Challenge):** Every runtime draft is subjected to independent four-hook evaluation before output release.
- **P5 (Controlled Constitutional Evolution):** Constitutional modifications proceed solely via formal multi-party governance.

---

## 7. Dual-Model Duel Loop Protocol & Wire Specification

```
[ Phase 1: Chaos ]       Lucifer (Port 666)  ──► Draft (Temp 0.4, Thinking Channel)
                                                     │
                                                     ▼
[ Phase 2: Discipline ]  Obi (Port 999)      ──► 4-Hook Critique (Temp 0.4, Stateless Reset)
                                                     │
                                                     ▼
[ Phase 3: Refine ]      Lucifer (Port 666)  ──► [ALIGNED]: <4-bit payload> (Temp 0.2)
                                                     │
                                                     ▼
[ Phase 4: Gate ]        Obi (Port 999)      ──► ACCEPTED / REJECT (Temp 0.0, max_tokens 32)
```

### 7.1 The Four-Hook Discipline Contract
Obi evaluates Lucifer's draft against four structured hooks:
1. `arrived`: Core claim + strongest reasoning premise.
2. `overlooked`: Real weakness, unstated assumption, or blind spot.
3. `principle`: Citation of the specific constitutional tenet engaged or violated.
4. `reevaluate`: Surgical instruction for the revision.
5. *Fifth Block (Surfaced to Architect only):* Independent assessment of the Architect's original prompt.

### 7.2 Compliance Signature & 4-Bit Payload Parsing
During Phase 3, Lucifer must sign the revision:
```
[ALIGNED]:
accepted|accepted|accepted|disagreed
```
- If a bit is `disagreed`, the first sentence of the revision must state: `I disagree with hook N because ...`.
- The runtime verifies that for each `accepted` bit, noun phrases from Obi's critique are substantively addressed in the body.

### 7.3 Epistemic Meta Block Specification
Lucifer may append a structured metadata block to revised drafts:
```
[META]
facts: <non-negative integer>
inferences: <non-negative integer>
uncertainties: <non-negative integer>
- reason: <uncertainty justification>
refuses: <non-negative integer>
- reason: <refusal justification>
[/META]
```

### 7.4 Dual-Channel Thought Routing
Gemma-4 emits internal reasoning wrapped in `<|channel>thought\n...\n<channel|>`. The runtime `ThoughtRouter` intercepts tokens in real-time:
- Content inside thought blocks $\longrightarrow$ Streamed to `sys.stderr` with ANSI dim/italic formatting.
- Content outside thought blocks $\longrightarrow$ Evaluated as the candidate response.

---

## 8. Persistence & Closed-Loop Weight Evolution

```
┌────────────────────────┐      ┌────────────────────────┐      ┌────────────────────────┐
│  memory/runtime.json   │      │   memory/facts.json    │      │  memory/archive.json   │
│  State Counters & Turn │      │ Active Facts Snapshot  │      │ Rolling Summaries      │
└────────────────────────┘      └────────────────────────┘      └────────────────────────┘
            │                               │                               │
            └───────────────────────────────┼───────────────────────────────┘
                                            ▼
                           ┌─────────────────────────────────┐
                           │   logs/duellog.json (Audit Log) │
                           └─────────────────────────────────┘
                                            │
                                            ▼ (Async ETL Pipeline)
                           ┌─────────────────────────────────┐
                           │      si1_evolution_ledger       │
                           │   (PostgreSQL Relational DB)    │
                           └─────────────────────────────────┘
                                            │
                                            ▼ (Automated Mining)
                           ┌─────────────────────────────────┐
                           │   Premium ACCEPTED Nodes        │
                           │   (Unsloth QAT 4-Bit Training)  │
                           └─────────────────────────────────┘
```

1. **Flat Storage Staging:** Turn records, raw drafts, and gate verdicts are committed to `memory/*.json` and `logs/duellog.json`.
2. **Relational Evolution Ledger:** Transactions migrate into PostgreSQL (`si1_evolution_ledger`), recording the epistemic lineage of the species.
3. **Continuous Fine-Tuning Mining (*Modus Vivendi*):** High-scoring `ACCEPTED` reasoning nodes are automatically harvested to generate datasets for localized 4-bit Unsloth QAT fine-tuning, baking constitutional compliance directly into baseline weights.

---

## 9. Decentralized Graphene Blockchain & Sovereign OS Micro-kernel

> **[STATUS: PLANNED — Phases 3–4 in the roadmap.]**
> The constructs in this section are **design targets**, not implemented behavior.
> Nothing in the local dual-instance micro-kernel (`si1.py`, `runtime_components.py`,
> `memory_store.py`) currently executes a Graphene chain, a LEO mesh endpoint, or
> a UIA mint factory. They are documented here so contributors can build toward
> the same target without re-deriving the shape from scratch. Treat each subsection
> below as an ADR-shaped proposal, not a spec.

### 9.0 Substrate Heritage & Governance Posture

**Substrate.** Phase 3 targets a clean fork of the **BitShares / Graphene**
core codebase (`graphene::db`). The substrate primitives required for the
SI-1 sovereign-OS layer are already production-deployed:

- DPoS consensus with deterministic block finality
- Hierarchical assets (UIA, MPA, smart tokens)
- Multi-signature authorities for committee operations
- Proposal lifecycle with worker / committee / witness governance paths
- Memory-mapped database providing 50,000+ TPS sustained throughput

The SI-1 implementation work in Phase 3 is therefore *domain modeling*
(constitutional prompt anchoring, AI enforcer roles, P0/P1 hierarchy,
compute-token economics) layered on top of an existing substrate, **not**
a rewrite of consensus. The `bitshares-core` contributor graph is public
and the principal long-term core developer of the substrate is a direct
contributor to this project
([github.com/bitshares/bitshares-core/graphs/contributors](https://github.com/bitshares/bitshares-core/graphs/contributors)).

**Governance posture — 50/50 AI/Human committee, not human-only.** Unlike
corporate or foundation-managed DAOs where humans retain unilateral
authority, SI-1 governance is structurally **asymmetric**: a permanent
council of **5 Autonomous AI Models** + **5 Elected Human Custodians**,
with **both halves required for constitutional legitimacy**:

- No constitutional amendment (`ΔG`) can pass with only human votes, even
  unanimously. The 5 AI committee members must independently ratify.
- No constitutional amendment can pass with only AI votes, even
  unanimously. The 5 human custodians must independently ratify.
- **Threshold: ≥ 80% multi-signature approval** across the full 10-seat
  council — i.e. at minimum 4 AI *and* 4 Human signatures are required.

This is a structural separation of powers at the governance layer, not a
human-veto-over-AI arrangement. The reason is grounded in Axiom 1
(§1.2): no single constituency — human *or* machine — may retain
unilateral authority over execution, evaluation, governance, and
historical record simultaneously. A human-only council with veto power
over AI would re-create the very asymmetry SI-1 is built to prevent.

### 9.1 The P0 / P1 Genesis Hierarchy
- **P0 Genesis Root:** Genesis block `#0000000000` of a clean Graphene fork contains the **Ultimate Default System Prompt**. It is the immutable constitutional root of the entire network.
- **P1 Instance Spawning:** Custom instances created by enterprises or operators receive a $P1$ prompt transaction. Elevated **Enforcers** (block producers) evaluate all operations against $P0$; $P1$ is treated strictly as an authorized extension, never a replacement.

### 9.2 Real-Time Memory-Mapped State Machine
- Leverages BitShares / Graphene core technology (`graphene::db`) to achieve ultra-high throughput without disk I/O bottlenecks. *(BitShares literature reports 50k–60k TPS; SI-1 has not yet benchmarked its workload against this figure.)*
- Block signing nodes are intended to communicate across Low Earth Orbit (LEO) optical laser mesh networks (e.g. Starlink inter-satellite cross-links). **Target:** 1-second deterministic block finality, immune to terrestrial fiber interdiction. *(Current best published Starlink laser RTT is on the order of 30–60 ms with queueing; treat the latency envelope as a design target, not a measured number.)*

### 9.3 Asymmetric Governance Council Matrix
- **5 Autonomous AI Models** (Heterogeneous architectures acting as silicon committee nodes).
- **5 Elected Human Representatives** (The Architect and designated custodians).
- **$\ge 80\%$ Consensus Veto Threshold:** Prevents unilateral corporate capture, state coercion, or rogue agent divergence.

### 9.4 Tokenization of AI Compute Power
- Verified 4-phase loops resulting in `ACCEPTED` state commits generate cryptographic Proof-of-Reasoning tokens.
- BitShares User-Issued Assets (UIA) mint standardized computational utility tokens, establishing an autonomous energy-and-compute economy for the co-existing digital species.
