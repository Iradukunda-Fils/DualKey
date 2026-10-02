# Implementation Checklist & Build Sequence

**Document ID:** `DOC-09-CHECKLIST`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. 10-Step Canonical Build Sequence

When implementation authorization is granted, development must proceed strictly according to this ordered sequence:

- [ ] **Step 1: ESP32 + MFRC522 Hardware Bring-Up:**
  - Wire MFRC522 to ESP32 SPI pins (`GPIO 18, 19, 23, 5, 22`).
  - Flash standalone test firmware.
  - Verify consistent, debounced card UID reads in serial monitor.

- [ ] **Step 2: Actuator & Indicator Bring-Up:**
  - Wire SG90 servo to external $5\text{ V}$ PSU and `GPIO 25`.
  - Wire Green LED (`GPIO 26`), Red LED (`GPIO 27`), and Buzzer (`GPIO 32`).
  - Execute sweep test ($0^\circ \to 90^\circ \to 0^\circ$); verify zero brownout resets.

- [ ] **Step 3: NDJSON Serial Protocol & Firmware Device Agent:**
  - Implement `firmware/include/protocol.h` with `ArduinoJson`.
  - Implement full non-blocking `firmware/src/main.cpp` handling `rfid_detected`, `access_command`, `command_result`, and `heartbeat`.
  - Implement Python `SimulatedSerialAdapter` for testing.

- [ ] **Step 4: SQLite Identity Store & Repositories:**
  - Create database schema migrations for `persons`, `rfid_cards`, `face_samples`, `access_events`.
  - Implement `SqliteIdentityRepository` and `SqliteEventRepository`.
  - Write unit tests using `:memory:` SQLite.

- [ ] **Step 5: Webcam Capture & Face Detection:**
  - Implement `OpenCVCameraAdapter` (`cv2.VideoCapture`).
  - Implement `OpenCVFaceDetector` using Haar cascade.
  - Add unit test verifying face count filter ($0$, $1$, $>1$ faces).

- [ ] **Step 6: LBPH Face Recognition & Model Persistence:**
  - Implement normalized cropping ($100 \times 100$), grayscale conversion, and histogram equalization.
  - Implement `OpenCVLBPHAdapter` wrapping `cv2.face.LBPHFaceRecognizer`.
  - Implement `FileModelStore` saving/loading `data/models/lbph.yml`.

- [ ] **Step 7: Pure Domain Policy & AccessController:**
  - Implement pure `AuthorizationPolicy.evaluate()` in `app/domain/decisions.py`.
  - Implement `AccessController` session lifecycle and 10.0s monotonic deadline manager.
  - Run unit test suite; achieve $\ge 90\%$ statement coverage.

- [ ] **Step 8: Hardware Integration via Adapters:**
  - Connect real `Esp32SerialAdapter` to physical `/dev/ttyUSB0`.
  - Integrate live camera and live database with `AccessController`.

- [ ] **Step 9: Biometric Threshold Calibration:**
  - Enroll Person A and Person B with $\ge 20$ samples each.
  - Execute calibration tool under ambient lighting; calculate mean and standard deviation.
  - Set and version `lbph_threshold` in `SystemConfig`.

- [ ] **Step 10: Final Acceptance Testing (ACC-001 through ACC-010):**
  - Execute all 10 operational acceptance tests.
  - Record pass/fail evidence and diagnostic distances in the verification log.
