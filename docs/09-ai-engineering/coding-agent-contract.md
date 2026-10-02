# AI Coding Agent Engineering Contract

**Document ID:** `DOC-09-AGENT-CONTRACT`  
**Status:** Normative Engineering Law  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Preamble & Binding Mandate

This contract governs any AI coding assistant, autonomous agent, or human engineer contributing to the **DualKey** repository. The documentation in `docs/` is the authoritative source of truth. Code is subservient to documentation.

Any agent operating in this repository **must strictly pledge and adhere** to the 12 Engineering Commandments set forth below.

---

## 2. The 12 Engineering Commandments

1. **Read Requirements Before Implementation:** Never write a line of code without reading the corresponding requirement specifications in `docs/01-requirements/`.
2. **Do Not Change Documented Behavior Silently:** Interface definitions in `docs/04-interfaces/` and data schemas are binding. If a contract must change, an Architecture Decision Record (ADR) must be created and approved first.
3. **Do Not Remove Tests Because Implementation is Difficult:** If a test fails, the bug is in the implementation code or the test harness. Deleting or weakening requirements or tests is strictly prohibited.
4. **Do Not Lower Security Thresholds Simply to Make Tests Pass:** Never weaken the canonical authorization formula, the 10.0s monotonic deadline, or biometric thresholds to artificially force a passing test.
5. **Do Not Introduce an ML Model Without Recording its Source and License:** Every third-party model must be logged in `models/registry.json` with source URL, version, SHA-256 checksum, and verified permissive license (MIT, Apache 2.0). Avoid non-commercial models like InsightFace default weights.
6. **Do Not Fine-Tune Without an Explicit Evidence-Based Justification:** Pretrained embeddings with prototype averaging are mandatory for small user populations. Do not retrain deep models on 20 samples.
7. **Do Not Introduce Cloud Services When Local Inference is Sufficient:** The entire access pipeline must operate offline without cloud APIs or external network calls.
8. **Do Not Introduce Distributed Infrastructure to Solve a Single-Device Problem:** Avoid Docker, Kubernetes, Kafka, Redis, or microservices for this single-door setup.
9. **When Improving Implementation, Preserve Interface Contracts:** Keep domain policies decoupled from ML libraries (OpenCV, ONNX) and hardware via Ports.
10. **Every Architectural Change Requires an ADR:** New models, transports, or persistence engines require an accepted record in `docs/08-decisions/`.
11. **Every New Requirement Requires an Updated Requirement ID:** Maintain stable alphanumeric identifiers across all specifications.
12. **Every New Behavior Requires Tests and Documentation Updates:** Changes to runtime behavior must be traced to test cases and synchronized in docs.
