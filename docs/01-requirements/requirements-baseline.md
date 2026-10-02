# Requirements Baseline & Governance

**Document ID:** `DOC-01-BASELINE`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Baseline Authority

This document and its sibling files in `docs/01-requirements/` constitute the **normative functional and architectural requirements** for DualKey.

Every requirement has a stable, globally unique alphanumeric identifier. Requirements must never be anonymous, must never be silently modified or removed, and must be verified by explicit automated unit, integration, or hardware-in-the-loop tests.

### Requirement Namespace Summary

| Prefix | Domain | Range | Description |
| :--- | :--- | :--- | :--- |
| **`FR-xxx`** | Functional Requirements | `FR-001` – `FR-025` | Direct runtime capabilities and behavioral specifications. |
| **`NFR-xxx`**| Non-Functional Requirements | `NFR-001` – `NFR-008` | Performance, timing, maintainability, and privacy constraints. |
| **`SEC-xxx`**| Security Requirements | `SEC-001` – `SEC-007` | Two-factor enforcement, fail-closed boundaries, and limitations. |
| **`HW-xxx`** | Hardware Requirements | `HW-001` – `HW-006` | Electrical ratings, pinouts, power isolation, and sensor specs. |
| **`SW-xxx`** | Software Requirements | `SW-001` – `SW-006` | Python runtime, OpenCV versioning, SQLite, and OS dependencies. |
| **`ACC-xxx`**| Acceptance Criteria | `ACC-001` – `ACC-010` | Operational end-to-end acceptance scenarios. |
| **`TEST-xxx`**| Verification Test Cases | `TEST-AUTH-001`+ | Concrete test procedures mapping requirements to code. |

---

## 2. Requirement Governance & Change Control

1. **No Silent Changes:** An AI coding agent or human engineer is strictly prohibited from altering the text, intent, or numerical thresholds of any requirement without an accompanying Architecture Decision Record (ADR) approved by the Lead Architect.
2. **No Deletion for Convenience:** If an automated test fails, the agent must fix the implementation code or test harness. Under no circumstances may a requirement be modified or removed to make a test pass.
3. **Traceability Obligation:** Every implementation module and test must declare the specific requirement IDs it satisfies. Untraced code is considered extraneous and subject to removal.

---

## 3. Global Traceability Matrix Overview

```text
[Requirement ID]
       │
       ▼
[Design Artifact] (docs/02-architecture/ & docs/03-design/)
       │
       ▼
[Implementation Module] (app/ & firmware/)
       │
       ▼
[Verification Test Case] (tests/)
```

| Requirement Group | Primary Architectural Component | Implementation Modules | Verification Tests |
| :--- | :--- | :--- | :--- |
| `FR-001`, `FR-023`, `FR-024` | System Health & Lifecycle | `health_service.py`, `main.cpp` | `TEST-LIFE-001`, `TEST-LIFE-002` |
| `FR-002`, `FR-003` | RFID Ingestion & Identity Lookup | `sqlite_repositories.py`, `main.cpp` | `TEST-RFID-001`, `TEST-RFID-002` |
| `FR-004`, `FR-012` | Monotonic Session Window | `monotonic_clock.py`, `access_controller.py` | `TEST-TIME-001`, `TEST-TIME-002`, `ACC-004`, `ACC-005` |
| `FR-005`, `FR-006` | Frame Ingestion & Face Detection | `opencv_camera.py`, `face_detector.py` | `TEST-VIS-001`, `TEST-VIS-002`, `ACC-007` |
| `FR-007`, `FR-008` | LBPH Feature Extraction & Distance | `opencv_lbph.py`, `file_model_store.py` | `TEST-VIS-003`, `TEST-VIS-004` |
| `FR-009`, `FR-010`, `FR-011` | Authorization Policy & Stable Gate | `decisions.py`, `access_controller.py` | `TEST-AUTH-001`, `TEST-AUTH-002`, `ACC-001`, `ACC-002`, `ACC-006` |
| `FR-013`, `FR-014`, `FR-015`, `FR-016` | Actuator & Indicator Execution | `esp32_serial.py`, `main.cpp` | `TEST-HW-001`, `TEST-HW-002`, `ACC-001`, `ACC-002` |
| `FR-017`, `FR-018`, `FR-019` | NDJSON Protocol & Idempotency | `serial_message_contract.md`, `protocol.h` | `TEST-PROTO-001`, `TEST-PROTO-002` |
| `FR-020`, `FR-021`, `FR-022` | Enrollment & Audit Persistence | `enrollment_service.py`, `sqlite_repositories.py` | `TEST-ENROLL-001`, `TEST-AUDIT-001` |
| `FR-025`, `SEC-007` | Security Disclosure & Limitation | `biometric-limitations.md` | `ACC-010`, Documentation Audit |
