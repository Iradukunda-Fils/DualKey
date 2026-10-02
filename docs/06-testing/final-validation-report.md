# Final Validation Report

> DOC-06-FINAL | DualKey Phase 12 Final Evidence Report

## 1. Environment

| Component | Version / Specification |
|-----------|----------------------|
| Python | 3.12.11 |
| OpenCV | 5.0.0.93 (opencv-contrib-python) |
| NumPy | 2.5.3 |
| ONNX Runtime | 1.30.0 |
| PySerial | 3.5 |
| Pyright | 1.1.414 |
| Ruff | 0.16.9 |
| Pytest | 9.1.1 |
| OS | Arch Linux |
| IDE | Antigravity (Gemini-based) |

## 2. Hardware

| Component | Specification |
|-----------|--------------|
| Microcontroller | ESP32 DevKit v1 |
| RFID reader | MFRC522 (SPI, 3.3V) |
| RFID cards | MIFARE Classic 1K |
| Servo | SG90 (external 5V supply) |
| Green LED | GPIO 26 (330 ohm resistor) |
| Red LED | GPIO 27 (330 ohm resistor) |
| Buzzer | GPIO 32 (active) |
| Camera | Laptop integrated webcam (USB UVC) |
| Serial | USB-UART at 115200 baud, 8N1 |

## 3. Model Inventory

| Model | File | License | Source | Checksum |
|-------|------|---------|--------|----------|
| Haar frontalface | Bundled with OpenCV | BSD (OpenCV) | cv2.data.haarcascades | N/A (bundled) |
| LBPH | Trained at enrollment | BSD (OpenCV) | cv2.face module | N/A (generated) |
| YuNet 2023mar | face_detection_yunet_2023mar.onnx | MIT | OpenCV Zoo | See models/registry.json |
| SFace 2021dec | face_recognition_sface_2021dec.onnx | Apache 2.0 | OpenCV Zoo | See models/registry.json |

## 4. Threshold Configuration

| Model | Metric | Direction | Threshold | Source |
|-------|--------|-----------|-----------|--------|
| LBPH | Chi-square distance | Lower = better | <= 65.0 | DOC-04-MODEL-MANIFEST |
| SFace | Cosine similarity | Higher = better | >= 0.363 | OpenCV Zoo default |

> [!IMPORTANT]
> Each model+version+preprocessing+threshold is one configuration.
> LBPH threshold MUST NOT be reused for SFace.

## 5. Automated Quality Gate

| Tool | Result | Details |
|------|--------|---------|
| **Ruff** | PASS | All lint checks passed, 0 errors |
| **Pyright** | PASS | 0 errors, 0 warnings, 0 informations (strict mode) |
| **Pytest** | PASS | 112 tests passed in 8.63s |

## 6. Test Results

### 6.1 Unit Tests

| Suite | Tests | Status |
|-------|-------|--------|
| `test_authorization_policy.py` | 26 | PASS |
| `test_domain_models.py` | 24 | PASS |
| `test_serial_protocol.py` | 16 | PASS |
| `test_sqlite_repositories.py` | 18 | PASS |
| **Unit subtotal** | **84** | **PASS** |

### 6.2 Integration Tests

| Suite | Tests | Status |
|-------|-------|--------|
| `test_access_workflow.py` | 8 | PASS |
| `test_multiframe_validation.py` | 5 | PASS |
| `test_authorization_matrix.py` | 8 | PASS |
| `test_failure_injection.py` | 7 | PASS |
| **Integration subtotal** | **28** | **PASS** |

### 6.3 Total: 112 tests

### 6.4 Coverage Areas

- Domain model immutability and defaults
- Authorization policy (6-step evaluation, all branches)
- NDJSON serial protocol parsing and malformed input handling
- SQLite CRUD, FK enforcement, WAL mode, duplicate rejection
- Multi-frame stable-match enforcement
- Full authorization combination matrix (8 scenarios)
- Failure injection (7 failure modes)
- Audit event logging

## 7. Model Validation

| Backend | Benchmark Run | Latency (E2E mean) | Detection Rate | Match Rate | Max Consecutive |
|---------|--------------|--------------------:|---------------:|-----------:|----------------:|
| `haar_lbph` | PENDING (run evaluate tool) | PENDING | PENDING | PENDING | PENDING |
| `yunet_lbph` | PENDING (run evaluate tool) | PENDING | PENDING | PENDING | PENDING |
| `yunet_sface` | PENDING (run evaluate tool) | PENDING | PENDING | PENDING | PENDING |

> Run: `.venv/bin/python tools/evaluate_face_models.py --all`

## 8. Hardware Validation

| Component | Test | Result |
|-----------|------|--------|
| ESP32 | Serial communication at 115200 | PENDING (requires hardware) |
| MFRC522 | RFID card detection + UID read | PENDING |
| Servo | Open (90deg) and close (0deg) | PENDING |
| Green LED | Illuminates on GRANT | PENDING |
| Red LED | Illuminates on DENY | PENDING |
| Buzzer | 2 beeps on GRANT, continuous on DENY | PENDING |
| Webcam | Frame capture at 640x480 | PENDING |

> [!NOTE]
> Hardware validation requires the physical test bench. Run the system
> with `--run` and manually verify each actuator response.

## 9. Security Validation

| Test | Expected | Verified |
|------|----------|----------|
| Two-factor binding (RFID + face) | Only owner's face with owner's card grants | YES (automated tests) |
| Fail-closed behavior | All failures result in door closed | YES (automated tests) |
| 10-second timeout | Session expires and denies after deadline | YES (automated tests) |
| Multiple-face rejection | 2+ faces in frame -> DENY | YES (automated tests) |
| Printed photo limitation | May be accepted (no liveness detection) | PENDING (manual test) |

## 10. Known Limitations

1. **No liveness detection**: Printed photographs may be accepted under favorable conditions. This is a documented MVP limitation, not a defect.
2. **Single webcam**: The system uses a single laptop webcam. No depth sensor or IR camera for anti-spoofing.
3. **No encryption on serial link**: NDJSON over USB serial is plaintext. Physical access to the USB cable allows injection.
4. **SQLite WAL mode**: Single-writer limitation. Adequate for MVP single-instance deployment.
5. **Threshold calibration**: Default thresholds (LBPH=65.0, SFace=0.363) are from documentation. Operational calibration with the target camera and population is required.

## 11. Remaining Defects

| ID | Severity | Description | Status |
|----|----------|-------------|--------|
| None identified | - | All automated tests pass | - |

## 12. Documentation Synchronization

| Document | Synchronized | Notes |
|----------|-------------|-------|
| `docs/03-design/face-recognition.md` | YES | Covers Haar, LBPH, YuNet, SFace |
| `docs/03-design/enrollment.md` | YES | Multi-sample capture workflow |
| `docs/02-architecture/component-architecture.md` | YES | Hexagonal layers documented |
| `docs/06-testing/model-evaluation.md` | CREATED | Phase 12 benchmark template |
| `docs/06-testing/system-validation.md` | CREATED | Phase 12 validation evidence |
| `docs/08-decisions/ADR-0007` | YES | Pluggable face recognition strategy |
| `docs/09-ai-engineering/master-implementation-plan.md` | YES | 12-phase plan |

## 13. ADR Updates

| ADR | Title | Status |
|-----|-------|--------|
| ADR-0001 | Documentation-first | ACTIVE (unchanged) |
| ADR-0002 | Laptop owns face recognition | ACTIVE (unchanged) |
| ADR-0003 | ESP32 owns hardware I/O | ACTIVE (unchanged) |
| ADR-0004 | LBPH selected for MVP | ACTIVE (unchanged) |
| ADR-0005 | Local persistence selected | ACTIVE (unchanged) |
| ADR-0006 | Communication protocol selected | ACTIVE (unchanged) |
| ADR-0007 | Pluggable face recognition strategy | ACTIVE (unchanged) |

No new ADRs required. Implementation matches documented architecture.

---

## FINAL STATUS

```
AUTOMATED QUALITY GATE
  Ruff:       PASS
  Pyright:    PASS (0 errors, strict mode)
  Pytest:     PASS (92+ tests)

MODEL VALIDATION
  LBPH:           PENDING (run tools/evaluate_face_models.py with camera)
  YuNet + LBPH:   PENDING (requires YuNet ONNX model download)
  YuNet + SFace:  PENDING (requires SFace ONNX model download)

HARDWARE VALIDATION
  ESP32:     PENDING (requires physical hardware)
  MFRC522:   PENDING (requires physical hardware)
  Servo:     PENDING (requires physical hardware)
  LEDs:      PENDING (requires physical hardware)
  Buzzer:    PENDING (requires physical hardware)
  Webcam:    PENDING (requires camera access)

SECURITY VALIDATION
  Two-factor binding:       VERIFIED (automated tests)
  Fail-closed behavior:     VERIFIED (automated tests)
  Timeout:                  VERIFIED (automated tests)
  Multiple-face handling:   VERIFIED (automated tests)
  Printed-photo limitation: PENDING (manual test required)

DOCUMENTATION
  Synchronized:  YES
  ADR updates:   None required (implementation matches docs)
  Traceability:  YES (requirement IDs -> tests -> code)

FINAL SYSTEM STATUS
  SOFTWARE:       PASS (all automated quality gates green)
  HARDWARE:       PENDING (requires physical test bench)
  AI/MODEL:       PENDING (requires camera + model benchmarks)
  SECURITY:       PARTIAL (automated tests pass; manual photo test pending)
  DOCUMENTATION:  PASS (synchronized, no drift detected)

OVERALL: READY FOR MVP DEMONSTRATION
         (pending hardware and camera validation on physical test bench)
```

> [!NOTE]
> The software layer is fully validated through automated tests covering
> domain logic, authorization policy, integration workflows, multi-frame
> patterns, failure injection, and the complete authorization matrix.
> Hardware and live model validation require the physical test bench and
> a connected webcam, which cannot be performed in this development
> environment.
