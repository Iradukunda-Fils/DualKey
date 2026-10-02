# Low-Level Design (LLD) & Implementation Blueprint

**Document ID:** `DOC-03-LLD`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Directory & Codebase Layout

The DualKey codebase is structured to enforce hexagonal decoupling between domain logic, orchestration services, hardware ports, and concrete adapters.

```text
DualKey/
├── docs/                                # Documentation architecture & engineering source of truth
├── app/
│   ├── __init__.py
│   ├── config.py                        # SystemConfig dataclass and environment loader
│   ├── main.py                          # Application entry point and cooperative event loop
│   ├── domain/                          # Pure business entities & policies (ZERO external dependencies)
│   │   ├── __init__.py
│   │   ├── models.py                    # Person, RFIDCard, FaceSample, AccessSession dataclasses
│   │   ├── states.py                    # SessionState enum
│   │   ├── decisions.py                 # AuthorizationPolicy, AccessDecision, DecisionResult
│   │   └── reason_codes.py              # ReasonCode enum (MATCHED_OWNER, TIMEOUT, etc.)
│   ├── application/                     # Orchestration services & use-case managers
│   │   ├── __init__.py
│   │   ├── access_controller.py         # Main session workflow & 10.0s monotonic deadline manager
│   │   ├── enrollment_service.py        # Multi-sample capture, LBPH training, and card association
│   │   ├── health_service.py            # Hardware link, camera, and database health monitor
│   │   └── event_logger.py              # Structured audit record builder
│   ├── ports/                           # Abstract structural interfaces (typing.Protocol)
│   │   ├── __init__.py
│   │   ├── camera.py                    # CameraPort
│   │   ├── recognizer.py                # FaceRecognizerPort, FaceDetectorPort
│   │   ├── device_transport.py          # DeviceTransportPort
│   │   ├── repositories.py              # IdentityRepository, EventRepository
│   │   ├── model_store.py               # ModelStorePort
│   │   └── clock.py                     # ClockPort
│   └── adapters/                        # Concrete implementations of ports
│       ├── __init__.py
│       ├── esp32_serial.py              # PySerial NDJSON transport adapter
│       ├── opencv_camera.py             # cv2.VideoCapture UVC driver
│       ├── opencv_lbph.py               # cv2.CascadeClassifier + cv2.face.LBPHFaceRecognizer
│       ├── sqlite_repositories.py       # sqlite3 database repository implementation
│       ├── file_model_store.py          # Filesystem YAML/XML model serialization
│       └── monotonic_clock.py           # time.monotonic() wrapper
├── firmware/                            # ESP32 C++ PlatformIO / Arduino project
│   ├── platformio.ini                   # Target: esp32doit-devkit-v1, framework: arduino
│   ├── include/
│   │   ├── config.h                     # Pin mapping & timing constants
│   │   ├── protocol.h                   # NDJSON schema structs & ArduinoJson serialization
│   │   └── rfid_driver.h                # MFRC522 SPI reader wrapper
│   └── src/
│       └── main.cpp                     # FreeRTOS setup, UART loop, PWM servo controller
├── data/                                # Local runtime artifacts (gitignored)
│   ├── app.db                           # Local SQLite 3 relational database
│   ├── faces/                           # Directory of captured training faces by person_id
│   ├── models/                          # Serialized trained model (lbph.yml)
│   └── logs/                            # JSONL audit event logs
└── tests/
    ├── unit/                            # Unit tests for domain, policy, protocol parsing
    ├── integration/                     # Simulated hardware, in-memory SQLite, camera mock tests
    └── hardware/                        # Hardware-in-the-loop (HIL) manual test scripts
```

---

## 2. Low-Level Module Responsibilities

### 2.1 Domain Layer (`app/domain/`)
* **`models.py`:** Contains plain immutable data structures (`Person`, `RFIDCard`, `FaceSample`, `AccessSession`). No business logic or I/O.
* **`states.py`:** Defines `SessionState(Enum)`: `IDLE`, `CARD_VALIDATING`, `VERIFYING`, `GRANTED`, `DENIED`, `TIMEOUT`, `FAULT`.
* **`decisions.py`:** Houses `AuthorizationPolicy.evaluate()`. Pure, deterministic function taking `(session, recognition_result, current_time, config)` and returning an `AccessDecision`.
* **`reason_codes.py`:** Enumerates exact machine-readable audit reasons (`MATCHED_OWNER`, `FACE_MISMATCH`, `MULTIPLE_FACES`, `TIMEOUT`, `UNKNOWN_RFID`, `LOW_CONFIDENCE`, etc.).

### 2.2 Application Layer (`app/application/`)
* **`access_controller.py`:** Executes the cooperative main loop tick. Reads transport events, spawns sessions, queries repositories, drives camera frame capture, feeds biometric models, invokes policy, and dispatches actuator commands.
* **`enrollment_service.py`:** Guides interactive sample collection, rejects frames lacking exactly 1 face, invokes model training, and writes person records.
* **`health_service.py`:** Checks device heartbeat freshness ($\le 3.0\text{ s}$), camera connectivity, and storage readiness.

### 2.3 Ports & Adapters Layer (`app/ports/`, `app/adapters/`)
* Declares standard protocols using Python's `typing.Protocol` with runtime checkability.
* Decouples external library updates (e.g. `opencv-python`) from core domain code.
