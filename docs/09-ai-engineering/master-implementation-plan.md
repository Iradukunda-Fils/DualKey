# DualKey — Master Implementation Plan (Phases 1–12)

**Document ID:** `DOC-09-PLAN`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Executive Implementation Strategy

DualKey is built strictly according to a 12-phase incremental engineering plan. The plan respects hexagonal architecture: the pure domain core is built first with zero dependencies, followed by abstract ports, test fixtures, concrete adapters, and finally end-to-end integration and hardware-in-the-loop (HIL) verification.

```text
Phase 1: Foundation (Directories, Manifests, Venv)
   ↓
Phase 2: Domain Core (Pure Models, States, Policy) ────> Unit Tests Pass
   ↓
Phase 3: Ports / Interfaces (typing.Protocol)
   ↓
Phase 4: Persistence (SQLite, WAL, Audit Repositories)
   ↓
Phase 5: Transport (NDJSON Serial Adapter + Simulated Device)
   ↓
Phase 6: Baseline Vision (Haar Cascade + OpenCV LBPH) ──> Baseline Tests Pass
   ↓
Phase 7: Modern AI Backend (YuNet Detector + SFace Recognizer)
   ↓
Phase 8: Enrollment Service (Multi-sample crops & Prototypes)
   ↓
Phase 9: ESP32 Firmware (C++ PlatformIO, MFRC522 SPI, PWM Servo)
   ↓
Phase 10: Access Workflow (AccessController, Main Loop, CLI)
   ↓
Phase 11: Security & Negative Testing (All 14 Failure Modes)
   ↓
Phase 12: Evidence Evaluation & Final Sign-Off
```

---

## 2. Phase-by-Phase Execution Breakdown

### Phase 1: Repository Foundation & Model Registry
* **Objective:** Establish physical directory tree, Python dependencies, model manifest, and Git ignores.
* **Deliverables:**
  * Directories: `app/domain/`, `app/application/`, `app/ports/`, `app/adapters/`, `firmware/include/`, `firmware/src/`, `tests/unit/`, `tests/integration/`, `tools/`, `models/lbph/`, `models/sface/`, `data/faces/`, `data/models/`, `data/logs/`.
  * `.gitignore`: Ignore `.venv/`, `data/*.db`, `data/faces/`, `data/models/*.yml`, `data/logs/`.
  * `models/registry.json`: Governed model manifest declaring Haar, LBPH, YuNet, and SFace with license metadata and checksums.
* **Gate:** Python virtual environment verified with `opencv-contrib-python`, `pyserial`, `pytest`, `ruff`, `mypy`.

### Phase 2: Domain Core (Zero External Dependencies)
* **Objective:** Implement pure data structures and deterministic authorization policy.
* **Deliverables:**
  * `app/domain/models.py`: `Person`, `RFIDCard`, `FaceSample`, `AccessSession`, `AccessEvent`, `SystemConfig`.
  * `app/domain/states.py`: `SessionState` Enum (`IDLE`, `CARD_VALIDATING`, `VERIFYING`, `GRANTED`, `DENIED`, `TIMEOUT`, `FAULT`).
  * `app/domain/reason_codes.py`: `ReasonCode` Enum (`MATCHED_OWNER`, `FACE_MISMATCH`, etc.).
  * `app/domain/decisions.py`: Pure `AuthorizationPolicy.evaluate()`.
* **Tests:** `tests/unit/test_authorization_policy.py` verifying all truth-table permutations and fail-closed conditions.
* **Gate:** 100% statement coverage on `app/domain/`. Zero imports of `cv2`, `serial`, `sqlite3`.

### Phase 3: Interface Protocols (Ports)
* **Objective:** Formalize runtime-checkable structural typing contracts.
* **Deliverables:**
  * `app/ports/camera.py`: `CameraPort`.
  * `app/ports/detector.py`: `FaceDetectorPort` and `DetectedFace`.
  * `app/ports/recognizer.py`: `FaceRecognizerPort` and `RecognitionResult`.
  * `app/ports/device_transport.py`: `DeviceTransportPort`, `DeviceEvent`, `DeviceCommand`.
  * `app/ports/repositories.py`: `IdentityRepository`, `EventRepository`.
  * `app/ports/clock.py`: `ClockPort`.
* **Gate:** `mypy --strict app/ports/` passes with zero errors.

### Phase 4: Local Persistence Layer
* **Objective:** Implement ACID relational storage and audit trail using SQLite 3.
* **Deliverables:**
  * `app/adapters/sqlite_repositories.py`: `SqliteIdentityRepository` and `SqliteEventRepository`.
  * Schema initialization: tables `persons`, `rfid_cards`, `face_samples`, `access_events` with WAL mode and foreign keys enabled.
* **Tests:** `tests/unit/test_sqlite_repositories.py` using in-memory SQLite (`:memory:`).

### Phase 5: Hardware Transport & Simulated Device
* **Objective:** Implement serial NDJSON communication framing, correlation tracking, and an in-memory device simulator for testing.
* **Deliverables:**
  * `app/adapters/esp32_serial.py`: Non-blocking serial polling, buffer splitting, NDJSON serialization.
  * `tests/integration/simulated_esp32.py`: In-memory simulated device implementing firmware state machine.
* **Tests:** `tests/unit/test_serial_protocol.py` (malformed JSON, framing errors, command acknowledgements).

### Phase 6: Face Recognition Baseline (Haar + LBPH)
* **Objective:** Implement the mandatory educational biometric baseline.
* **Deliverables:**
  * `app/adapters/opencv_camera.py`: `OpenCVCameraAdapter` with frame rate control.
  * `app/adapters/haar_detector.py`: `HaarFaceDetector` wrapping `haarcascade_frontalface_default.xml`.
  * `app/adapters/lbph_recognizer.py`: `LBPHRecognizer` ($100 \times 100$ crop, `equalizeHist()`, `LBPHFaceRecognizer`).
  * `app/adapters/file_model_store.py`: Model disk serialization (`data/models/lbph.yml`).
* **Tests:** `tests/unit/test_lbph_recognizer.py` verifying prediction, distance calculation, and model saving/loading.

### Phase 7: Modern Model Backend (YuNet + SFace)
* **Objective:** Implement modern open-source deep learning inference without fine-tuning.
* **Deliverables:**
  * Model artifacts placed under `models/yunet/` and `models/sface/` with verified checksums.
  * `app/adapters/yunet_detector.py`: `YuNetFaceDetector` using OpenCV `cv2.FaceDetectorYN` (with 5-point landmark alignment).
  * `app/adapters/sface_recognizer.py`: `SFaceRecognizer` using OpenCV `cv2.FaceRecognizerSF` (128D embeddings, cosine similarity, prototype averaging).
  * `tools/evaluate_face_models.py`: Evidence-based benchmarking utility comparing LBPH vs YuNet+SFace.
* **Tests:** `tests/unit/test_sface_recognizer.py` and benchmark execution.

### Phase 8: Unified Enrollment Service
* **Objective:** Implement multi-sample interactive enrollment supporting both backends.
* **Deliverables:**
  * `app/application/enrollment_service.py`: Guiding 20-sample capture, pose variation, quality filtering.
  * Dual storage update: retrains LBPH (`lbph.yml`) and computes SFace prototype vector (`sface_prototypes.json`).
* **Tests:** `tests/integration/test_enrollment_service.py`.

### Phase 9: ESP32 Firmware Implementation
* **Objective:** Complete physical C++ microcontroller firmware.
* **Deliverables:**
  * `firmware/platformio.ini`: ESP32 DevKit v1 board target.
  * `firmware/include/config.h`: GPIO pin assignments, PWM constants.
  * `firmware/include/protocol.h`: ArduinoJson serialization/deserialization.
  * `firmware/src/main.cpp`: FreeRTOS non-blocking event loop (MFRC522 SPI poller, LEDC servo PWM driver, LED/buzzer indicator controller, autonomous 3000ms hold timer).

### Phase 10: Full Access Workflow Orchestration
* **Objective:** Wire end-to-end access control loop into the main application.
* **Deliverables:**
  * `app/application/access_controller.py`: Coordinating session spawning, 10.0s monotonic deadline, frame evaluation, stable-match gate ($N=3$), and actuator dispatch.
  * `app/main.py`: CLI entry point supporting `--run`, `--enroll`, `--calibrate`, `--model {lbph,sface}`.
* **Tests:** `tests/integration/test_access_workflow.py` executing full end-to-end sessions with simulated devices.

### Phase 11: Security Validation & Negative Test Suite
* **Objective:** Validate all 14 failure modes and 10 acceptance criteria.
* **Deliverables:**
  * Automated execution of `TEST-AUTH-001` through `TEST-AUTH-014`.
  * Verification of fail-closed behavior on cable severance, camera loss, and corrupted commands.

### Phase 12: Final Evaluation, Documentation Updates & Sign-Off
* **Objective:** Record empirical benchmark results and finalize runbooks.
* **Deliverables:**
  * `docs/06-testing/model-evaluation.md`: Benchmark results table.
  * `docs/06-testing/system-validation.md`: Traceability verification report.
  * `docs/07-operations/final-runbook.md`: Production operator guide.
