# SI-1 Architecture

SI-1 began as a prompt-response experiment and evolved through constrained prompting, iterative human feedback, recursive protocol refinement, and continuity-based interaction loops.

The project now separates four concerns:

- Protocol: the cooperation and reasoning rules in `core/protocol.md`.
- Abstract: the conceptual runtime model in `core/abstract.md`.
- Runtime prompt: the active system prompt in `core/system.md`.
- Execution: the local runtime implementation in `si1.py`.

The architectural direction is to move from one-off prompting toward a persistent cognition-layer orchestration system. The runtime should preserve independent reasoning, compact memory, explicit uncertainty, and resistance to self-reinforcing inference loops.
