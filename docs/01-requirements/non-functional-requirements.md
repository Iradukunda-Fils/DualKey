# Non-Functional Requirements Specification

**Document ID:** `DOC-01-NFR`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Overview

Non-functional requirements specify the architectural qualities, performance ceilings, timing guarantees, and maintainability boundaries that govern the DualKey access control system.

---

## 2. Requirement Specifications

### NFR-001: Responsiveness & Latency
* **Statement:** The system shall initiate biometric verification promptly upon RFID presentation and deliver local physical feedback with minimal perceived latency.
* **Metric:**
  * RFID detection to host session start: $\le 150\text{ ms}$.
  * Camera frame acquisition and face detection cycle: $\ge 15\text{ FPS}$ on standard laptop CPU (cycle time $\le 66\text{ ms}$ per frame).
  * Decision execution to servo actuation start: $\le 100\text{ ms}$ after the third stable match is confirmed.

### NFR-002: Timing Precision
* **Statement:** The 10.0-second verification window must be strictly measured against a monotonic clock source.
* **Metric:** The host timer shall utilize Python's `time.monotonic()` to guarantee immunity against system clock drift, daylight saving transitions, or NTP synchronization jumps. Timeout evaluation error margin shall not exceed $\pm 50\text{ ms}$.

### NFR-003: Reliability & Fail-Closed Robustness
* **Statement:** The system shall maintain fail-closed physical security under all unexpected error conditions, including peripheral disconnects, data corruption, or process termination.
* **Metric:** $100\%$ of injected fault conditions (camera disconnect, USB unplug, malformed JSON, firmware crash) must leave the servo in the locked position ($0^\circ$). Zero uncommanded actuator releases are permitted.

### NFR-004: Maintainability & Architectural Decoupling
* **Statement:** The codebase shall strictly decouple business logic from external frameworks, hardware drivers, and machine learning libraries.
* **Metric:**
  * Core domain entities and the `AuthorizationPolicy` must have zero imports of `cv2`, `serial`, `sqlite3`, or `RPi.GPIO`.
  * All I/O operations must be accessed exclusively through Python `typing.Protocol` interfaces (Ports).

### NFR-005: Determinism & Policy Isolation
* **Statement:** Authorization decisions must be fully deterministic and reproducible given identical inputs.
* **Metric:** The `AuthorizationPolicy.evaluate()` method must be a pure, side-effect-free function. Biometric recognizer outputs (`label`, `distance`) must exist purely as data structures; they must possess no direct capability to trigger actuators, manipulate serial lines, or modify persistent state.

### NFR-006: Observability & Auditability
* **Statement:** All critical state transitions, raw sensor inputs, biometric distances, decisions, and system errors must be traceable via structured logs.
* **Metric:** Every session attempt must output an immutable NDJSON or SQLite record containing the complete correlation tuple `(event_id, session_id, command_id, timestamp, rfid_uid, expected_person, recognized_person, distance, decision, reason)`.

### NFR-007: Scalability Seams
* **Statement:** The software architecture shall provide explicit decoupling seams allowing future replacement of components without modifying the core domain logic.
* **Metric:** Swapping the persistence layer (SQLite to PostgreSQL), the computer vision adapter (LBPH to FaceNet/ONNX), or the device link (Serial to TCP/IP Gateway) must require modifications strictly to adapter classes, requiring zero alterations to `AccessController` or `AuthorizationPolicy`.

### NFR-008: Local Privacy & Data Sovereignity
* **Statement:** Biometric data and access telemetry shall remain completely confined to the local host machine by default.
* **Metric:** Zero outbound network calls, telemetry beacons, or cloud API integrations shall be executed during routine operation or enrollment. Facial sample images and model files must reside exclusively in local directory paths (`data/faces/`, `data/models/`).
