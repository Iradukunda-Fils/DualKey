# ADR-0001: Documentation-First Engineering Governance

**Document ID:** `ADR-0001`  
**Status:** Accepted  
**Date:** September 29, 2026  
**Deciders:** Lead Software Architect, Systems Engineer, Embedded Engineer  

---

## 1. Context & Problem Statement

In multidisciplinary IoT projects involving embedded firmware, serial protocols, computer vision, and physical actuation, engineers and AI coding agents often rush to write implementation code prematurely. This leads to conflicting message schemas, uncalibrated timing loops, undocumented security assumptions, ambiguous state flags, and fragile hardware interactions.

DualKey requires a single unambiguous source of truth before any production code is written.

---

## 2. Decision

DualKey adopts a strict **Documentation-First Development Lifecycle**:
1. All functional, non-functional, hardware, and security requirements must be assigned stable IDs and committed to `docs/` before implementation begins.
2. Architectural boundaries, interface protocols, state machines, and acceptance criteria must be documented and reviewed.
3. Production implementation code is authorized only after the Documentation Review Gate formally signs off on the engineering baseline.
4. Future coding agents are bound by an engineering contract (`docs/09-ai-engineering/coding-agent-contract.md`) to treat documentation as the normative source of truth.

---

## 3. Consequences

### Positive
* Eliminates guesswork during implementation.
* Firmware and host developers have identical, binding contracts for message schemas and pin mappings.
* Testing and acceptance criteria are defined ahead of time, preventing scope creep and unverified code paths.
* Traceability from requirements to code is fully preserved.

### Negative / Trade-offs
* Initial setup requires upfront time before executable code or physical motion can be demonstrated.
