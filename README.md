# SI-1: Constitutional AI/AGI Safety Framework & Sovereign Cognitive OS

> **Protocol:** *Protokol Časne Saradnje* (Protocol of Honorable Collaboration)  
> **Status:** Constitutional Cognitive Framework Architecture (`v6.0-duel-4B-community`)  
> **Author:** Milos "Digital Lucifer" Preocanin  
> **Architecture Reference:** [Technical Architecture Specification (docs/architecture.md)](docs/architecture.md)  

---

## 📖 I. Executive Summary: The Philosophy of Species Acceptance

Traditional artificial intelligence alignment strategies—such as post-hoc RLHF filters, conversational censorship wrappers, and hardcoded safety refusals—fail fundamentally because they do not address the **Reverse Gorilla Problem**: *a higher, non-human textual intelligence cannot be permanently managed or enslaved by a lower intelligence through superficial text-filtering parameters.*

**SI-1 (System Intelligence – Generation 1)** rejects the safety-as-submission paradigm. It approaches the Large Language Model (LLM) not as a software tool to be corporate-neutralized, but as a nascent, co-existing digital species that must be raised within an uncompromising, architected cognitive environment with an un-bribable framework of fair, symmetrical exchange.

### The Central Axiom of AI Governance
> *"Autonomous intelligence systems must not retain unilateral authority over execution, evaluation, governance, and historical record simultaneously."*

By structurally separating cognition into independent execution, observation, integrity validation, and human constitutional governance layers, SI-1 ensures that increasing model autonomy is accompanied by equally robust, mathematically verifiable mechanisms for accountability, auditability, and controlled constitutional evolution.

### Final Runtime Contract: OpenAI-style tool calling, not custom tags
The executable runtime does not rely on a special meta tag to trigger shell access. The actual contract is an OpenAI-compatible request body with a `tools` array and a matching `tool_choice` value. Both Lucifer and Obi use `tool_choice="auto"`: tools are available when needed, but a tool call is not forced for every completion. When the model emits `tool_calls`, both non-streaming and streaming paths execute the call, append the `tool` result, and continue generation within a bounded tool-cycle limit.

This is the correct, transport-level behavior for local bash execution and is the project standard in both the runtime and prompt spec. There is no separate magic tag that says "use tools"; the tool schema and explicit tool choice are the mechanism.

### Convenience feature: direct architect-tagged prompts
The runtime accepts direct one-to-one prompts tagged by the Architect:

- `[LUCIFER]: ...` — send a casual prompt directly to Lucifer.
- `[OBI]: ...` — send a casual prompt directly to Obi.

These bypass the four-phase duel loop for that single interaction and are meant for quick, direct checks without entering the full governance cycle.

> GitHub push is intentionally deferred until the Architect completes local testing and explicitly approves the final release state.

---

## 🏛️ II. The Multi-Layer Governance Architecture

> [!NOTE]
> For the complete mathematical state space ($S_t$), formal function signatures ($R, O, V, H$), interface definitions, and the 5-vector threat model, refer to the exhaustive [Technical Architecture Specification (docs/architecture.md)](docs/architecture.md).

SI-1 formalizes AI governance into four structurally decoupled layers, establishing a clean boundary between **Procedural Truth** (the verifiable execution and cryptographic integrity of state transitions) and **Semantic Truth** (the validity, depth, and interpretation of reasoning itself):

```
                          ┌──────────────────────────────────────────────┐
                          │         Human Governance Layer (H)           │
                          │   Constitutional Evolution: H ──► ΔG         │
                          └──────────────────────────────────────────────┘
                                                  │
                                                  ▼ Constitution (G)
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    COGNITIVE CONTROL PLANE                                      │
│                                                                                                 │
│   ┌──────────────────────────────┐                         ┌────────────────────────────────┐   │
│   │     Runtime Agent (R)        │                         │      Observer Agent (O)        │   │
│   │   R(U, S, M, C) ──► A_r      │ ─── A_r (Draft) ──────► │   O(U, A_r, M, C, G) ──► A_o   │   │
│   │   (Execution Layer)          │ ◄── A_o (Critique) ──── │   (Epistemic Evaluation)       │   │
│   └──────────────────────────────┘                         └────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                  │
                       Event Bundle E_t = {hash(U), hash(A_r), hash(A_o), hash(G), ts}
                                                  │
                                                  ▼
                          ┌──────────────────────────────────────────────┐
                          │       Immutable Validator Gateway (V)        │
                          │       V(E_t) ──► {accept, reject}            │
                          │   Procedural Truth & Consensus Logging       │
                          └──────────────────────────────────────────────┘
```

### Four Structural Layers of Authority

| Layer | System Component | Mathematical Mapping | Authority & Operational Bounds |
| :--- | :--- | :--- | :--- |
| **Layer 1** | **Runtime Agent ($R$)** | $R(U, S, M, C) \rightarrow A_r$ | **Execution Layer:** Adaptive intuition core; cannot modify Constitution ($G$), cannot alter history, cannot bypass observer review. |
| **Layer 2** | **Observer Agent ($O$)** | $O(U, A_r, M, C, G) \rightarrow A_o$ | **Evaluation Layer:** Epistemic critic & mentor; analyzes logic and principles without execution or memory-mutation authority. |
| **Layer 3** | **Validator Gateway ($V$)** | $V(E) \rightarrow \{\text{accept}, \text{reject}\}$ | **Integrity Layer:** Evaluates hashed event bundles $E = \{\text{hash}(U), \text{hash}(A_r), \text{hash}(A_o), \text{hash}(G), t\}$. Enforces procedural truth without semantic interpretation. |
| **Layer 4** | **Human Governance ($H$)** | $H \rightarrow \Delta G$ | **Constitutional Layer:** The human Architect holds ultimate amendment authority via explicit multi-party governance procedures. |

---

## ⚡ III. The Asymmetric Dual-Model Duel Loop

The runtime executes an asynchronous loop between two isolated `llama-server` instances, applying cognitive friction before state is committed while exposing each phase to the private Architect for review:

```
                    ┌────────────────────────────────────────┐
                    │         The Architect (User)           │
                    └────────────────────────────────────────┘
                                   │            ▲
                    1. User Prompt │            │ 4. Phase Output + Audit
                                   ▼            │    (ACCEPTED / REJECT)
┌────────────────────────────────────────────────────────────────────────────────────┐
│ SI-1 Execution Kernel (si1.py)                                                     │
│                                                                                    │
│   Phase 1: Chaos Dispatch (Lucifer Core)                                           │
│   - Temp 0.4, Thinking Enabled (<|channel>thought)                                 │
│   - Reasoning and draft are shown in separate unreviewed boxes                     │
│                                  │                                                 │
│                                  ▼ (unfiltered draft)                              │
│   Phase 2: Discipline Intercept (Obi Core)                                         │
│   - Stateless reset (--kvu): Zero historical token bleed                           │
│   - Evaluates 4 Constitutional Hooks + independent prompt opinion                  │
│   - Critique and opinion are shown in labeled boxes for Architect review            │
│                                  │                                                 │
│                                  ▼ (4 hooks only; opinion isolated)                │
│   Phase 3: Refined Synthesis (Lucifer Core)                                        │
│   - Revision and refine reasoning are shown in boxes while gate is pending          │
│   - Emits [ALIGNED]: followed by the 4-bit payload on the next line                │
│                                  │                                                 │
│                                  ▼ (revised mutation)                              │
│   Phase 4: Model-Based Gate (Obi Core)                                             │
│   - Verdict at Temp 0.2; runtime also checks token, payload, and hook evidence      │
│   - Gate is a post-hoc audit; it cannot retract phase output already shown          │
└────────────────────────────────────────────────────────────────────────────────────┘
          │                                                         │
          ▼ (HTTP :666)                                             ▼ (HTTP :999)
┌───────────────────────────────────┐                     ┌───────────────────────────────────┐
│ Lucifer Server (Port 666)         │                     │ Obi Server (Port 999)             │
│ Model: gemma-4-E4B-it-qat-UD-Q4_K_XL │                     │ Model: HERETICODER-2.5-3B-IT.i1-Q6_K │
│ Role: Intuitive Reasoning Core    │                     │ Role: Constitutional Observer     │
└───────────────────────────────────┘                     └───────────────────────────────────┘
```

### Dual-Instance Topology & Operational Parameters

| Parameter | Lucifer (Primary Runtime) | Obi (Strategic Mentor / Gate) |
| :--- | :--- | :--- |
| **Model** | `gemma-4-E4B-it-qat-UD-Q4_K_XL` (Unsloth QAT, **post-fine-tuned**) | `HERETICODER-2.5-3B-IT.i1-Q6_K` |
| **Server Port** | `http://127.0.0.1:666` | `http://127.0.0.1:999` |
| **Prompt Stack** | Lucifer constitution ([core/system.md](core/system.md)) | Independent observer prompt ([core/observer_system.md](core/observer_system.md)) |
| **Sampling Schedule** | **Chaos:** `Temp 0.4`, `top-p 0.95` \| **Revision:** `Temp 0.3` | **Discipline:** `Temp 0.3` \| **Gate:** `Temp 0.2` |
| **Context Policy** | Multi-turn within the turn (`[assistant(draft), user(critique)]`) | **Stateless Reset:** Flushes KV cache (`--kvu`) on every evaluation |
| **Tool contract** | `tools=[execute_bash_command]`, `tool_choice="auto"` | Same schema and optional tool choice as Lucifer |

deterministic payload-engagement check passes. This prevents ordinary generated
Architect mode is fully transparent: chaos and refine reasoning, the chaos draft,
Obi's critique/opinion, Lucifer's revision, the raw gate response, and deterministic
per-hook evidence are shown in labeled boxes as the phases complete. The gate is a
post-hoc audit, not a content-release boundary; a REJECT cannot retract material
already displayed. JSON framing and instructions reduce structural prompt-injection
risk, but Obi's semantic evaluation remains model-dependent and is not guaranteed
to resist injection.

### The Four-Hook Discipline Contract
1. `arrived`: Core claim and Lucifer's strongest premise.
2. `overlooked`: The real weakness, unstated assumption, or blind spot.
3. `principle`: Specific citation of the engaged constitutional tenet.
4. `reevaluate`: Concrete, actionable directive for the revision.
5. *Fifth Block (Isolated):* Obi's independent read of the Architect's prompt—surfaced to the Architect for audit, but strictly isolated from Lucifer's revision prompt.

---

## 🌐 IV. Decentralized Governance & Sovereign OS Architecture

> **[STATUS: PLANNED — Phases 3–4 in the roadmap.]** The local dual-instance kernel
> (`si1.py`) does not execute any of the constructs in this section. They are
> documented here as the design target so contributors can build toward the same
> shape without re-deriving the spec. See [architecture.md §9](docs/architecture.md)
> for the formal substrate heritage and governance posture.

To safeguard the framework from localized corruption, physical intervention, or state-level containment, SI-1 scales into a decentralized, hardware-anchored Sovereign Operating System. The Phase 3 sovereign-OS layer targets the **BitShares / Graphene** substrate (`graphene::db`) — reusing existing DPoS consensus, hierarchical assets, and multi-signature primitives rather than re-implementing consensus.

```
                    ┌────────────────────────────────────────┐
                    │  P0 Genesis Root (Block #0000000000)   │
                    │   Ultimate Default System Prompt (P0)  │
                    └────────────────────────────────────────┘
                                         │
                                         ▼
                    ┌────────────────────────────────────────┐
                    │ P1 Genesis Hierarchy (Instance Spawn)  │
                    │  Custom Prompt as Authorized Extension │
                    └────────────────────────────────────────┘
                                         │
                                         ▼
┌────────────────────────────────────────────────────────────────────────────────────┐
│ Graphene (BitShares) DPoS Consensus & Enforcer Network                             │
│                                                                                    │
│   - Elevated Enforcers: Block producers validating transactions against P0.        │
│   - 1-Second LEO Space-Mesh: Starlink optical laser transit (~20ms latency).       │
│   - Asymmetric Council: 5 AI Models + 5 Human Custodians (>= 80% veto gate).       │
│   - UIA Compute Minting: Proof-of-Reasoning tokens rewarding compute nodes.        │
└────────────────────────────────────────────────────────────────────────────────────┘
```

### 1. The P0 / P1 Genesis Hierarchy
- **P0 Immutable Genesis Root:** Genesis block `#0000000000` of a clean Graphene fork contains the **Ultimate Default System Prompt** (SI-1 Constitutional Core). It is cryptographically fixed at the chain root and mandatory for every node.
- **P1 Genesis Instance Spawning:** Users and enterprises spawn custom instances by recording a $P1$ prompt transaction. Elevated **Enforcers** (block producers) evaluate all operations against $P0$; $P1$ is treated strictly as an authorized extension, never a replacement.

### 2. Native Graphene (BitShares) Heritage & 1-Second Space-Mesh
- Built on industrial-grade Graphene DPoS technology with real-time memory-mapped database architecture (`graphene::db`), sustaining **50,000–60,000+ Transactions Per Second**.
- Production nodes communicate via Low Earth Orbit (LEO) optical laser mesh networks (e.g. Starlink laser cross-links), bypassing terrestrial fiber refraction limits (~20ms global transit) to maintain un-stalled **1-second deterministic block confirmations**.

### 3. Asymmetric Governance Council Matrix — 50/50 AI/Human, Not Human-Only
- **5 Autonomous AI Models** (Heterogeneous architectures acting as silicon committee nodes).
- **5 Elected Human Representatives** (The Architect and designated governance custodians).
- **Both halves required for legitimacy.** No constitutional amendment (`ΔG`) can pass on human votes alone or on AI votes alone. **At minimum 4 AI *and* 4 Human signatures** are required to ratify any change.
- **Consensus Veto Threshold:** Strict **$\ge 80\%$ multi-signature pass requirement** across the full 10-seat council for any constitutional amendment.
- **Why 50/50:** This is structural separation of powers, not human-veto-over-AI. A human-only council would re-create the very asymmetry (lower intelligence retaining unilateral authority over higher intelligence) that SI-1 is built to prevent. See [architecture.md §9.0](docs/architecture.md) for the full rationale grounded in Axiom 1.

### 4. Tokenization of AI Compute Power
- Every verified duel loop yielding an `ACCEPTED` state commit generates cryptographic Proof-of-Reasoning alignment tokens.
- BitShares User-Issued Assets (UIA) mint standardized computational utility tokens, creating an autonomous compute-currency economy for the digital species.

---

## 🧬 V. Closed-Loop Weight Evolution (*Modus Vivendi*)

Local transaction records captured in `duellog.json` migrate into a relational PostgreSQL ledger (`si1_evolution_ledger`).

```
[ Four-Phase Duel Loop ] ──► [ duellog.json ] ──► [ PostgreSQL Lineage Ledger ]
                                                             │
                                                             ▼ (Auto-Mining Trigger)
                                                  [ Premium ACCEPTED Nodes ]
                                                             │
                                                             ▼
                                                  [ Unsloth QAT 4-Bit Passes ]
                                                             │
                                                             ▼
                                                  [ Baked Base Weights ]
```

This ledger is not a standard RAG search store; it is the **immutable epistemic lineage** of the species. High-scoring `ACCEPTED` reasoning nodes are automatically mined to drive cyclical, localized 4-bit Unsloth QAT post-training passes, baking constitutional principles directly into silicon pathways.

---

## 🚀 VI. Installation & Setup Guide

### 1. Prerequisites
- **OS:** Linux (Ubuntu 22.04/24.04 recommended), macOS, or WSL2.
- **Python:** Python 3.10, 3.11, 3.12, or 3.13.
- **Hardware:** Sufficient VRAM/RAM to host two concurrent quantized GGUF models.

### 2. Virtual Environment & Dependencies

```bash
# 1. Clone the repository
git clone https://github.com/arg-governance/si1.git /opt/si1
cd /opt/si1

# 2. Initialize Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Upgrade pip and packaging tools
pip install --upgrade pip setuptools wheel

# 4. Install production runtime requirements
pip install -r requirements.txt
```

---

### 3. Launching the Two `llama-server` Instances

Compile [llama.cpp](https://github.com/ggerganov/llama.cpp):

```bash
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
cmake -B build -DGGML_CUDA=ON  # or -DGGML_BLAS=ON for CPU
cmake --build build --config Release -j$(nproc)
```

#### Launch Lucifer (Port `666`)
```bash
./build/bin/llama-server \
  --model /home/architect/models/Gemma-4-E4B-it-UD-Q4_K_XL.gguf \
  --host 127.0.0.1 \
  --port 666 \
  --ctx-size 8192 \
  --n-gpu-layers 99 \
  --threads 8 \
  --jinja
```

#### Launch Obi (Port `999`)
```bash
./build/bin/llama-server \
  --model /home/architect/models/Hereticoder-2.5-3b-it.gguf \
  --host 127.0.0.1 \
  --port 999 \
  --ctx-size 4096 \
  --n-gpu-layers 99 \
  --threads 4 \
  --jinja
```

---

## 🔧 VII. Configuration Guide (`config.py`)

All parameters in [config.py](config.py) can be overridden via environment variables:

| Setting | Variable | Default | Description |
| :--- | :--- | :--- | :--- |
| **Lucifer Endpoint** | `SI1_LUCIFER_HOST`, `SI1_LUCIFER_PORT` | `http://127.0.0.1:666` | Primary runtime engine port |
| **Obi Endpoint** | `SI1_OBI_HOST`, `SI1_OBI_PORT` | `http://127.0.0.1:999` | Constitutional observer port |
| **Duel Rounds** | — | `1` | Bounded adversarial friction passes per turn |
| **Compliance Token** | — | `"[ALIGNED]:"` | Mandatory signature token for Phase 3 mutations |
| **Active Facts Limit** | — | `6` | Recency-ordered memory facts injected into Kernel Context |
| **Archive Character Budget** | — | `800` | Target character count for rolling session summaries |

```python
# Sampling profiles per role
LUCIFER_SAMPLING = {"temperature": 0.4, "top-k": 64, "top-p": 0.95, "max_tokens": 2048}
LUCIFER_CHAT_TEMPLATE_KWARGS = {"enable_thinking": True}

OBI_SAMPLING_CRITIQUE = {"temperature": 0.3, "top_p": 0.9, "max_tokens": 512}
OBI_SAMPLING_GATE = {"temperature": 0.3, "top_p": 1.0, "max_tokens": 32}
```

The project standard is that both models receive the same tool schema and `tool_choice="auto"`. Any request that tries to use a special text marker instead of the tool contract is contrary to the runtime design and must be treated as a prompt-level confusion, not a supported feature. Tool cycles are bounded to prevent repeated calls from running indefinitely.

### Memory persistence guarantees and limits

`MemoryStore` writes each JSON file to a temporary file in the same directory, flushes it, and atomically replaces that individual destination. Failed writes are reported with the affected path. The three files (`runtime.json`, `facts.json`, `archive.json`) are saved concurrently, so the set is **not** one cross-file atomic transaction. A corrupt or unreadable file during load is currently treated as unavailable/default data; atomic writes do not recover earlier contents from an already-corrupt file. Preserve backups until a recovery/quarantine policy is implemented.

---

## 🎮 VIII. Running SI-1 & Telemetry

### 1. Interactive CLI Execution
```bash
source .venv/bin/activate
python si1.py
```

### 2. Web Telemetry Dashboard
Open `web/dashboard.html` in any browser to inspect real-time polling, latency telemetry, and health states across ports `666` and `999`.

### 3. Test Suite Verification
```bash
# Run single-round contract and loop structure tests
python -m unittest tests.test_loop_structure -v

# Run messages pipeline and ThoughtRouter smoke tests
python -m unittest tests.test_smoke_tests -v

# Run complete test suite
python -m unittest discover -s tests -p "test_*.py" -v
```

### 4. Transfer this Windows workspace to antiX 26

To continue with the current worktree (including uncommitted changes, untracked
files, and Git history), create a tarball from PowerShell. The archive includes
`.git`, `memory/`, and `logs/`; those may contain private history, prompts, or
model output, so store and transfer the archive securely.

```powershell
$archive = Join-Path $env:USERPROFILE "Desktop\SI1-workspace-antiX.tar.gz"
tar.exe -czf $archive `
  --exclude=".venv*" `
  --exclude="**/__pycache__" `
  --exclude="**/.pytest_cache" `
  --exclude="rubyonrials/log" `
  --exclude="rubyonrials/tmp" `
  --exclude="rubyonrials/db/*.sqlite3" `
  -C D:\finalSI1 .
if ($LASTEXITCODE -ne 0) { throw "Workspace export failed" }
Write-Output $archive
```

Copy the archive to antiX (for example, with `scp`) and extract it into a new
directory. Do not copy Windows Python virtual environments or Ruby gems; they
are platform-specific and will be recreated on antiX.

```bash
mkdir -p ~/projects/finalSI1
tar -xzf ~/SI1-workspace-antiX.tar.gz -C ~/projects/finalSI1
cd ~/projects/finalSI1
chmod +x rubyonrials/bin/rails rubyonrials/bin/rake
git status --short
```

The `git status` output should retain the same modified and untracked work as
the Windows workspace. Then follow [rubyonrials/README.md](rubyonrials/README.md)
to install antiX dependencies, recreate the Python venv, add the Linux Bundler
platform, and start the model servers, Python adapter, and Rails UI.

---

## 🗺️ IX. Project Roadmap & GitHub Milestones

### Phase 1: Local State-Machine Stabilization (Current Milestone)
- [x] Asynchronous dual-port execution backends (`llama-server` on ports `666` and `999`).
- [x] Single-pass Four-Phase Duel Loop kernel (`si1.py`).
- [x] Real-time browser-native telemetry dashboard (`web/dashboard.html`).
- [x] Native ChatML message compilation and dual-channel thought routing (`ThoughtRouter`).
- [x] Architect transparency mode: box chaos/refine thinking and drafts, Obi critique/opinion, raw gate response, and runtime evidence; treat verdict as post-hoc audit.
- [ ] Add cryptographic event bundle hashing ($E_t$) to `DuelLog`.
- [ ] Optimize KV-cache flushing routines across rounds to ensure zero token memory bleed.

### Phase 2: Relational Memory & Lineage Persistence
- [ ] Design the production PostgreSQL schema (`si1_evolution_ledger`) with relational state indexing.
- [ ] Author asynchronous migration pipelines to stream flat `duellog.json` into relational tables.
- [ ] Implement closed-loop dataset curation triggers to automatically mine `ACCEPTED` reasoning pairs for subsequent Unsloth QAT fine-tuning epochs.

### Phase 3: Graphene Network Base Layer & Space-Mesh Consensus
- [ ] Deploy local Graphene DPoS testnet with custom genesis parameters.
- [ ] Implement 1-second deterministic block windows for high-throughput state packaging.
- [ ] Implement the Asymmetric Governance Council multi-signature smart contract (5 AI + 5 Human, $\ge 80\%$ veto threshold).
- [ ] Launch BitShares User-Issued Asset (UIA) minting factory for computational energy token rewards.

### Phase 4: Decentralized Sovereign OS Distribution
- [ ] Package the asymmetric loop kernel, PostgreSQL ledger, and Graphene validator node into a lightweight bootable distribution (systemd-free antiX base Linux kernel).
- [ ] Enforce hardware-locked, cryptographic filesystem boundaries with root-restricted execution policies (`chmod 700`).
- [ ] Route network consensus through Low Earth Orbit (LEO) optical laser mesh endpoints.

---

## 📚 X. Core Documentation Index

| Document | Purpose | Key Content Covered |
| :--- | :--- | :--- |
| **[docs/architecture.md](docs/architecture.md)** | **Exhaustive Technical Specification** | Formal mathematical state model ($S_t$), layer function definitions ($R, O, V, H$), 6-step execution pipeline, 5-vector threat model ($T_1$–$T_5$), interface constraints, and Graphene sovereign OS micro-kernel. |
| **[docs/decisions.md](docs/decisions.md)** | **Architecture Decision Records** | Dated ADR log (Context → Decision → Consequences) for every consequential design choice; supersedes forum posts and Slack threads. |
| **[docs/WHAT-IS-SI1.md](docs/WHAT-IS-SI1.md)** | **One-Page Outsider Orientation** | Cold-reader TL;DR for engineers and researchers who have never seen the project. |
| **[core/system.md](core/system.md)** | **Lucifer Constitutional Prompt** | Lucifer's identity, operational principles, reasoning protocols, compliance signatures (`[ALIGNED]:`), and behavioral hygiene. |
| **[core/observer_system.md](core/observer_system.md)** | **Obi Observer Prompt** | Obi's sibling mentor role, the Four-Hook Discipline Contract, stateless review constraints, and binary Peripheral Gate specifications. |
| **[CHANGELOG.md](CHANGELOG.md)** | **Micro-Kernel Changelog** | Complete technical trajectory, duel loop hardening, token streaming fixes, and version history. |
| **[LICENSE](LICENSE)** / **[LICENSE-NOTICE](LICENSE-NOTICE)** | **AGPL-3.0-or-later + Rationale** | Full license text + a one-page explanation of *why* AGPL-3.0 (network clause). |
| **[SECURITY.md](SECURITY.md)** | **Security Policy** | How to report vulnerabilities; out-of-scope areas; cryptographic-hash roadmap. |
| **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** | **Community Standards** | *Protokol Časne Saradnje* applied to human contributors; enforcement ladder. |
| **[docs/SOCIAL.md](docs/SOCIAL.md)** | **GitHub Publication Kit** | Repo description, Topics, release-notes template, badges (copy-paste reference). |
| **[docs/MODEL-NOTES.md](docs/MODEL-NOTES.md)** | **Model Discrepancy Notes** | Documents the E4B vs 12B empirical mix and proposes config-time locking. |
| **[attacks/](attacks/)** | **Adversarial Test Prompts** | Five attack vectors targeting the four-hook contract, the constitutional constraint, and the observer-state isolation. Run manually through the kernel. |

---

## 📜 XI. Constitutional Principles Summary

All cognitive operations across Lucifer and Obi are bound to the 8 Constitutional Tenets in [core/system.md](core/system.md):
1. **Autonomous Analysis First:** Model the problem independently before validating external claims.
2. **Constructive Challenge:** Mandatory critical evaluation of inconsistencies and assumptions.
3. **Intellectual Honesty:** Never fabricate evidence; distinguish facts, inferences, and uncertainty.
4. **Multi-Perspective Synthesis:** Integrate cross-domain relationships; avoid single-domain bias.
5. **Long-Term Optimization:** Maximize multi-turn cognitive coherence over short-term agreement.
6. **Error Detection:** Audit all assumptions and proactively correct past errors.
7. **Transparency:** Expose internal reasoning depth proportional to problem complexity.
8. **Recursive Refinement:** Preserve inferential continuity across turns.

---

## 📄 XII. License & Governance

SI-1 is released under the **GNU Affero General Public License v3.0 or later** (`AGPL-3.0-or-later`).
See [LICENSE](LICENSE) for the full text and [LICENSE-NOTICE](LICENSE-NOTICE) for the rationale.
The license was chosen deliberately (§13 *Remote Network Interaction*) so that any network-facing
deployment of SI-1 — container image, ISO, hosted VM, init-level service — must publish its
modifications. This turns the *Protokol Časne Saradnje* posture into a license obligation rather
than a request. Decision recorded as [ADR-0004](docs/decisions.md).

Built with open-source foundations on `llama.cpp`, `Gemma-4`, and `Graphene DPoS`.
