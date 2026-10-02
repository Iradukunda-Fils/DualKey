# Unit Testing Specification

**Document ID:** `DOC-06-UNIT`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Scope of Unit Tests

Unit tests validate isolated modules in `app/domain/`, `app/application/`, and `app/adapters/` with zero dependency on physical hardware or operating system peripherals.

---

## 2. Core Unit Test Battery

| Test ID | Module Tested | Input Scenario | Expected Output | Traced Requirement |
| :--- | :--- | :--- | :--- | :--- |
| `TEST-UNIT-AUTH-001` | `decisions.py` | Valid session, recognized face matches card owner, distance $\le 50$, count $= 1$. | `result == CONTINUE`, `reason == MATCH_IN_PROGRESS`, `match_count == 1`. | `FR-009`, `FR-010` |
| `TEST-UNIT-AUTH-002` | `decisions.py` | 3rd consecutive positive match for expected owner. | `result == GRANT`, `reason == MATCHED_OWNER`. | `FR-010`, `SEC-001` |
| `TEST-UNIT-AUTH-003` | `decisions.py` | Recognized face matches enrolled user other than card owner. | `result == DENY`, `reason == FACE_MISMATCH`. | `FR-011`, `SEC-001` |
| `TEST-UNIT-AUTH-004` | `decisions.py` | Detected face has distance $85.0 > 65.0$ (threshold). | `result == CONTINUE`, `reason == LOW_CONFIDENCE`. | `FR-008` |
| `TEST-UNIT-AUTH-005` | `decisions.py` | Zero faces detected in frame. | `result == CONTINUE`, `reason == FACE_NOT_FOUND`. | `FR-006` |
| `TEST-UNIT-AUTH-006` | `decisions.py` | Frame contains 2 faces. | `result == DENY`, `reason == MULTIPLE_FACES`. | `FR-006` |
| `TEST-UNIT-AUTH-007` | `decisions.py` | Current monotonic time $\ge \text{deadline}$. | `result == DENY`, `reason == TIMEOUT`. | `FR-004`, `FR-012` |
| `TEST-UNIT-PROTO-001`| `protocol.py` | Valid `rfid_detected` JSON string. | Parsed `DeviceEvent` object with correct `uid` and `event_id`. | `FR-017` |
| `TEST-UNIT-PROTO-002`| `protocol.py` | Corrupted JSON or missing `v: 1` field. | Parse returns `None`; raises no uncaught exceptions. | `FR-019` |
| `TEST-UNIT-REPO-001` | `sqlite_repo.py` | In-memory SQLite: query unknown card UID. | Returns `None`. | `FR-003` |
| `TEST-UNIT-REPO-002` | `sqlite_repo.py` | In-memory SQLite: insert person and bind card. | `get_card_owner()` returns expected `Person`. | `FR-003`, `FR-020` |
