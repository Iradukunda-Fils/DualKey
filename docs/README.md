# DualKey — Documentation Index & Architecture Master

**Document ID:** `DOC-INDEX-00`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. What is DualKey?

**DualKey** is a physical two-factor access-control engineering prototype. It binds physical credential possession with biometric identity verification using two distinct devices:
1. **Physical Token Possession:** An RFID card read via an NXP MFRC522 sensor connected to an Espressif ESP32 microcontroller.
2. **Biometric Face Verification:** Live webcam facial capture processed by a laptop host running OpenCV's Local Binary Patterns Histograms (LBPH) face recognizer.

Access is granted **only** when a valid, enrolled RFID card is presented and the corresponding card owner's face is positively identified within an active 10-second verification window.

```text
+-----------------------+         +----------------------------+
|  Possession Factor    |         |     Biometric Factor       |
|  (RFID Card via ESP32)|         | (Webcam + LBPH via Laptop) |
+-----------+-----------+         +--------------+-------------+
            |                                    |
            +-----------------+------------------+
                              |
                              v
                 +--------------------------+
                 | 10-Second Monotonic      |
                 | Verification Window      |
                 +------------+-------------+
                              |
                              v
                 +--------------------------+
                 | Authoritative Decision   |
                 | (Laptop Core Policy)     |
                 +------------+-------------+
                              |
                     [ACCESS_GRANTED]
                              |
                              v
                 +--------------------------+
                 | ESP32 Actuation          |
                 | (Servo Open / Green LED) |
                 +--------------------------+
```

> [!IMPORTANT]
> **Prototype Classification:** DualKey is an MVP and educational systems-engineering prototype. It demonstrates strict two-factor binding, fail-closed safety, and clean separation of concerns. It is **not** a production-grade physical security controller, does not include presentation-attack (liveness) detection, and uses cloneable RFID UIDs.

---

## 2. Engineering Lifecycle & Traceability

The project adheres to a strict documentation-first engineering lifecycle. No implementation code is written without explicit trace back to requirements, architectural design, interface contracts, and acceptance criteria.

```text
Requirements (01-requirements/)
      ↓
Architecture (02-architecture/)
      ↓
Detailed Design (03-design/)
      ↓
Interfaces & Contracts (04-interfaces/)
      ↓
Security Baseline (05-security/)
      ↓
Test Strategy & Cases (06-testing/)
      ↓
Documentation Review Gate (Section 22)
      ↓
Implementation (firmware/ & app/)
```

### Traceability Vector Example
```text
FR-009 (Identity Binding)
   ↓
Component: Authorization Engine (docs/03-design/authorization-engine.md)
   ↓
Module: app/domain/decisions.py & app/application/access_controller.py
   ↓
Test Case: TEST-AUTH-002 / ACC-002
```

---

## 3. Documentation Hierarchy & Authorities

The documentation is organized into 10 structured domains. Each domain is authoritative for specific system concerns:

| Directory | Concern & Authority | Authoritative Documents |
| :--- | :--- | :--- |
| `00-project/` | Project scope, charter, terminology, assumptions, and constraints. | [project-charter.md](file:///home/iradukunda/Lost/Learn/Auca-Innovation/IoT/DualKey/docs/00-project/project-charter.md), [scope.md](file:///home/iradukunda/Lost/Learn/Auca-Innovation/IoT/DualKey/docs/00-project/scope.md) |
| `01-requirements/` | Functional, non-functional, security, hardware, software requirements, and acceptance baseline. | [requirements-baseline.md](file:///home/iradukunda/Lost/Learn/Auca-Innovation/IoT/DualKey/docs/01-requirements/requirements-baseline.md), [functional-requirements.md](file:///home/iradukunda/Lost/Learn/Auca-Innovation/IoT/DualKey/docs/01-requirements/functional-requirements.md) |
| `02-architecture/` | System context, high-level design (HLD), runtime component model, deployment topology, and state machine. | [architecture-overview.md](file:///home/iradukunda/Lost/Learn/Auca-Innovation/IoT/DualKey/docs/02-architecture/architecture-overview.md), [high-level-design.md](file:///home/iradukunda/Lost/Learn/Auca-Innovation/IoT/DualKey/docs/02-architecture/high-level-design.md) |
| `03-design/` | Low-level design (LLD), authorization engine logic, face processing pipeline, enrollment, and persistence models. | [low-level-design.md](file:///home/iradukunda/Lost/Learn/Auca-Innovation/IoT/DualKey/docs/03-design/low-level-design.md), [authorization-engine.md](file:///home/iradukunda/Lost/Learn/Auca-Innovation/IoT/DualKey/docs/03-design/authorization-engine.md) |
| `04-interfaces/` | Serial NDJSON message contracts, internal Python Protocols (Ports), error codes, and baud configurations. | [serial-message-contract.md](file:///home/iradukunda/Lost/Learn/Auca-Innovation/IoT/DualKey/docs/04-interfaces/serial-message-contract.md), [internal-interfaces.md](file:///home/iradukunda/Lost/Learn/Auca-Innovation/IoT/DualKey/docs/04-interfaces/internal-interfaces.md) |
| `05-security/` | Threat model (STRIDE), security boundaries, biometric spoofing limitations, and fail-closed policies. | [threat-model.md](file:///home/iradukunda/Lost/Learn/Auca-Innovation/IoT/DualKey/docs/05-security/threat-model.md), [biometric-limitations.md](file:///home/iradukunda/Lost/Learn/Auca-Innovation/IoT/DualKey/docs/05-security/biometric-limitations.md) |
| `06-testing/` | Test pyramid, test strategy, unit tests, integration harnesses, and HIL (Hardware-in-the-Loop) test procedures. | [test-strategy.md](file:///home/iradukunda/Lost/Learn/Auca-Innovation/IoT/DualKey/docs/06-testing/test-strategy.md), [test-cases.md](file:///home/iradukunda/Lost/Learn/Auca-Innovation/IoT/DualKey/docs/06-testing/test-cases.md) |
| `07-operations/` | Setup guide, environment configuration, troubleshooting, wiring diagrams, and operator runbooks. | [setup.md](file:///home/iradukunda/Lost/Learn/Auca-Innovation/IoT/DualKey/docs/07-operations/setup.md), [configuration.md](file:///home/iradukunda/Lost/Learn/Auca-Innovation/IoT/DualKey/docs/07-operations/configuration.md) |
| `08-decisions/` | Architecture Decision Records (ADRs) tracking architectural rationale, context, and consequences. | [ADR-0001-documentation-first.md](file:///home/iradukunda/Lost/Learn/Auca-Innovation/IoT/DualKey/docs/08-decisions/ADR-0001-documentation-first.md) |
| `09-ai-engineering/`| Rules, boundaries, and contracts governing AI coding agents working on this codebase. | [coding-agent-contract.md](file:///home/iradukunda/Lost/Learn/Auca-Innovation/IoT/DualKey/docs/09-ai-engineering/coding-agent-contract.md) |

---

## 4. Key Architectural Boundaries

1. **Laptop Host vs. ESP32 Microcontroller:**
   - **Laptop Host:** Orchestrates workflow, manages SQLite persistence, executes face detection and LBPH recognition, enforces authorization policy, maintains session timers, and writes audit logs.
   - **ESP32 Device:** Manages MFRC522 SPI communications, transmits detected card UIDs, listens for cryptographically unauthenticated local access commands, moves the servo PWM, and drives status LEDs and the buzzer.
   - **Separation Law:** The ESP32 *never* makes authorization or biometric decisions. The Laptop *never* drives physical GPIO directly.

2. **Core Authorization Formula:**
   ```text
   GRANT iff:
       active_rfid == True
       AND now < session.deadline
       AND exactly_one_usable_face == True
       AND lbph_distance <= configured_threshold
       AND recognized_person == card_owner
       AND stable_match_count >= required_consistent_matches
   OTHERWISE:
       DENY / TIMEOUT / FAULT -> servo remains locked
   ```

---

## 5. Document Map & File Index

```text
docs/
├── README.md                                    # This document
│
├── 00-project/
│   ├── project-charter.md                       # Vision, objectives, stakeholders
│   ├── scope.md                                 # Explicit in-scope & out-of-scope boundaries
│   ├── glossary.md                              # Ubiquitous language & terms
│   └── assumptions-and-constraints.md           # Engineering assumptions & hardware constraints
│
├── 01-requirements/
│   ├── requirements-baseline.md                 # Baseline definition and change control
│   ├── functional-requirements.md               # FR-001 to FR-025 specification
│   ├── non-functional-requirements.md           # NFR-001 to NFR-008 performance & quality
│   ├── security-requirements.md                 # SEC-001 to SEC-007 access rules & limitations
│   ├── hardware-requirements.md                 # HW-001 to HW-006 electrical & pin specs
│   ├── software-requirements.md                 # SW-001 to SW-006 platform & runtime specs
│   └── acceptance-criteria.md                   # ACC-001 to ACC-010 user acceptance rules
│
├── 02-architecture/
│   ├── architecture-overview.md                 # System overview and core principles
│   ├── system-context.md                        # C4 Context diagram and external actors
│   ├── high-level-design.md                     # DOC-02 translation: layers & responsibilities
│   ├── component-architecture.md                # C4 Component diagram & ports/adapters
│   ├── deployment-architecture.md               # Hardware & software deployment topology
│   ├── data-flow.md                             # Sequence diagram for end-to-end flows
│   └── state-machine.md                         # Formal host & device state machines
│
├── 03-design/
│   ├── low-level-design.md                      # DOC-03 translation: module blueprints
│   ├── authorization-engine.md                  # Pure domain policy and evaluation logic
│   ├── face-recognition.md                      # OpenCV Haar/LBPH pipeline & thresholding
│   ├── enrollment.md                            # Multi-sample capture & model training
│   ├── identity-model.md                        # Relational domain entity definitions
│   ├── device-communication.md                  # Framing, parsing, and polling architecture
│   ├── hardware-control.md                      # ESP32 FreeRTOS/Arduino task & PWM loop
│   └── persistence.md                           # SQLite schema and model storage
│
├── 04-interfaces/
│   ├── esp32-protocol.md                        # Physical serial interface specifications
│   ├── serial-message-contract.md               # NDJSON schemas (events, commands, acks)
│   ├── internal-interfaces.md                   # Python typing.Protocol definitions
│   ├── model-manifest-schema.md                 # Model registry manifest schema & license rules
│   └── error-codes.md                           # Universal reason and error code catalog
│
├── 05-security/
│   ├── threat-model.md                          # STRIDE threat analysis matrix
│   ├── security-boundaries.md                   # Hardware, process, and memory boundaries
│   ├── authentication-and-authorization.md      # Dual-factor binding mechanics
│   ├── biometric-limitations.md                 # LBPH photo spoofing and attack disclosure
│   └── failure-and-recovery.md                  # Fail-closed mechanisms and watchdog states
│
├── 06-testing/
│   ├── test-strategy.md                         # Verification strategy & test pyramid
│   ├── unit-testing.md                          # Domain policy and protocol tests
│   ├── integration-testing.md                   # Adapter, camera, and simulated device tests
│   ├── hardware-in-loop-testing.md              # Physical breadboard test procedures
│   ├── acceptance-tests.md                      # ACC-001 through ACC-010 scenarios
│   └── test-cases.md                            # Complete TEST-AUTH-001..014 specifications
│
├── 07-operations/
│   ├── setup.md                                 # Hardware assembly and wiring setup
│   ├── development-environment.md               # Python virtualenv, udev rules, PlatformIO
│   ├── configuration.md                         # Config keys, defaults, and calibration
│   ├── troubleshooting.md                       # Common electrical and vision pitfalls
│   └── runbook.md                               # Daily operation, enrollment, and log triage
│
├── 08-decisions/
│   ├── README.md                                # ADR process overview and status log
│   ├── ADR-0001-documentation-first.md          # Architectural mandate for doc baseline
│   ├── ADR-0002-laptop-owns-face-recognition.md # Placement of biometric inference on laptop
│   ├── ADR-0003-esp32-owns-hardware-io.md       # Microcontroller isolation for GPIO/PWM
│   ├── ADR-0004-lbph-selected-for-mvp.md        # OpenCV LBPH vs Deep Learning models
│   ├── ADR-0005-local-persistence-selected.md   # SQLite and filesystem vs cloud/database
│   ├── ADR-0006-communication-protocol-selected.md # NDJSON over serial vs binary/Protobuf
│   └── ADR-0007-pluggable-face-recognition-strategy.md # Pluggable open-source face recognition
│
└── 09-ai-engineering/
    ├── ai-implementation-rules.md               # Strict constraints for autonomous agents
    ├── coding-agent-contract.md                 # 12-point engineering pledge for AI models
    └── implementation-checklist.md              # Step-by-step implementation verification
```
