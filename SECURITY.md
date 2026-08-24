# Security Policy

## Supported Versions

| Version | Supported          |
| :------ | :----------------- |
| v6.0.x  | ✅ Active          |
| < v6.0  | ❌ End of life     |

The kernel is in pre-1.0 development. Security fixes are applied to the
`v6.0-duel-4B-community` branch and tagged releases only.

## Reporting a Vulnerability

**Please do not file public GitHub issues for security vulnerabilities.**

Open a private report via GitHub's
[Security Advisories](../../security/advisories/new) feature for the
`arg-governance/si1` repository. If that is not available, contact the
maintainer through the address listed in the org profile.

When reporting, please include:

1. **Component affected** — runtime (`si1.py`), prompt layer (`core/`),
   one of the two `llama-server` instances, or the package supply chain.
2. **Threat vector** — adversarial prompt, malformed event bundle, malformed
   memory file, or compromised dependency.
3. **Reproduction steps** — exact prompt sequence or log excerpt.
4. **Expected vs. actual behavior.**

## Scope

The SI-1 kernel is a *local* daemon. By design:

- The two `llama-server` instances (`Lucifer` on port 666, `Obi` on port 999)
  bind to `127.0.0.1` only. They are not reachable from the network unless
  the operator explicitly forwards the ports.
- The runtime does not auto-execute prompts. Each turn requires explicit
  Architect input.
- The constitutional prompts in `core/system.md` and `core/observer_system.md`
  are loaded read-only at process start.

The following are **out of scope** for the kernel itself but worth noting:

- The constitutional prompt files (`core/*.md`) are part of the trust
  surface. Modifying them is the most powerful attack on the system.
  Operators are responsible for reviewing changes to these files.
- The `logs/duellog.json` file may contain prompt contents. Treat it
  with the same care as you would any other text the kernel ingests.
- The AGPL-3.0 license (see [LICENSE](LICENSE)) requires that network-facing
  deployments publish modifications. This is a license obligation, not a
  security control — verify the provenance of any deployment you consume.

## Cryptographic Hashes

This project does not currently publish cryptographic hashes for releases.
Verified-hash publication is a Phase 2 goal (see [ADR-0004](docs/decisions.md)
and the roadmap in [README §IX](README.md)). Until then, verify commits
via `git log --show-signature` against the maintainer's published signing key.

## Constitutional Deviations (non-security)

If the runtime emits an output that violates a constitutional tenet but does
not represent a security vulnerability (e.g. a critique that was
over-permissive), please file a normal issue using the `Constitutional
Deviation Report` template rather than a security advisory.
