# Functional Requirements Specification

**Document ID:** `DOC-01-FR`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Scope of Functional Requirements

This specification defines the 25 normative functional requirements (`FR-001` through `FR-025`) governing the DualKey access control system. Every requirement is testable and assigned to an authoritative component.

---

## 2. Requirement Specifications

### FR-001: Startup and Safe State
* **Statement:** The system shall initialize all hardware peripherals and software components into a verified locked safe state upon boot or reset.
* **Specification:** On power-up or firmware reboot, the ESP32 shall immediately position the servo to the locked position ($0^\circ$), extinguish the green LED, turn off the red LED, silence the buzzer, and report a healthy status before accepting any access commands. The laptop host shall verify database integrity and model existence before arming.
* **Owner:** Firmware Agent & Host Lifecycle.

### FR-002: RFID Detection
* **Statement:** The ESP32 shall continuously poll the MFRC522 RFID reader and report detected card UIDs to the host over the serial connection.
* **Specification:** When an ISO/IEC 14443 Type A RFID transponder enters the RF field, the ESP32 shall read its unique identifier (4-byte or 7-byte UID), construct an `rfid_detected` NDJSON message containing a unique `event_id` and the hex-encoded `uid`, and transmit it over UART within $100\text{ ms}$.
* **Owner:** ESP32 Firmware / Device Agent.

### FR-003: RFID Validation
* **Statement:** The host shall validate the reported RFID UID against the local identity store.
* **Specification:** Upon receiving `rfid_detected`, the host shall query the SQLite repository. If the UID matches an active enrolled `Person`, an `AccessSession` shall be instantiated. If the UID is unknown or marked inactive, the host shall reject the attempt immediately with reason `UNKNOWN_RFID` and transmit an `access_command` with decision `deny`.
* **Owner:** Host `AccessController` & `IdentityRepository`.

### FR-004: Verification Window
* **Statement:** A valid RFID event shall initiate a 10.0-second face-verification window measured via a monotonic clock.
* **Specification:** The host session manager shall set `deadline = time.monotonic() + 10.0`. The session shall remain in state `VERIFYING` until an authorization decision (`GRANT` or `DENY`) is reached or until `time.monotonic() >= deadline`.
* **Owner:** Host `AccessController`.

### FR-005: Camera Capture
* **Statement:** The host shall acquire video frames from the local webcam throughout the active verification window.
* **Specification:** The host shall poll frames from the camera adapter at $\ge 15\text{ FPS}$ with nominal resolution $640 \times 480$. Frame capture shall stop immediately when the session exits `VERIFYING`.
* **Owner:** `CameraPort` / `OpenCVCameraAdapter`.

### FR-006: Face Detection
* **Statement:** The host shall detect the presence and count of human faces in each acquired frame.
* **Specification:** Each frame shall be converted to grayscale and evaluated via an OpenCV Haar feature-based cascade classifier (`haarcascade_frontalface_default.xml`). The detector shall return zero, one, or multiple bounding boxes.
* **Owner:** Host Face Detector.

### FR-007: LBPH Recognition
* **Statement:** The host shall perform biometric feature extraction and classification using OpenCV's `LBPHFaceRecognizer`.
* **Specification:** When exactly one face is detected, the region of interest (ROI) shall be cropped, resized to standardized dimensions ($100 \times 100$ pixels), equalized via histogram equalization (`cv2.equalizeHist`), and passed to `LBPHFaceRecognizer.predict()`. The recognizer shall return an integer `label` and a float `distance`.
* **Owner:** `FaceRecognizerPort` / `OpenCVLBPHAdapter`.

### FR-008: Recognition Threshold
* **Statement:** The host shall evaluate the computed LBPH distance against a calibrated configuration threshold.
* **Specification:** A recognition result is valid if and only if `distance <= config.lbph_threshold`. Results where `distance > config.lbph_threshold` shall be classified as `LOW_CONFIDENCE` and shall never contribute to a grant.
* **Owner:** `AuthorizationPolicy`.

### FR-009: Identity Binding
* **Statement:** The system shall grant access only when the recognized face matches the enrolled owner of the presented RFID card.
* **Specification:** The recognized label from `FR-007` must map to a `person_id` that is identical to the `expected_person_id` of the active `AccessSession`.
* **Owner:** `AuthorizationPolicy`.

### FR-010: Stable-Match Gate
* **Statement:** An access grant shall require $N$ consecutive positive recognition matches for the expected identity.
* **Specification:** To prevent false positives caused by momentary image noise, the host shall maintain a counter `match_count`. Each consecutive frame confirming `FR-008` and `FR-009` increments `match_count`. Only when `match_count >= config.required_consistent_matches` (default $N = 3$) shall a `GRANT` decision be issued.
* **Owner:** `AuthorizationPolicy`.

### FR-011: Wrong-Face Denial
* **Statement:** The detection of an enrolled face belonging to an identity other than the card owner shall cause immediate access denial.
* **Specification:** If `LBPH.predict()` produces `distance <= threshold` but `person_id != expected_person_id`, the host shall not wait for the 10-second timeout. It shall immediately transition the session to `DENIED` with reason `FACE_MISMATCH` and issue a deny command.
* **Owner:** `AuthorizationPolicy`.

### FR-012: No-Face / Timeout Denial
* **Statement:** If no matching face is recognized before the 10.0-second window expires, the system shall deny access.
* **Specification:** If `time.monotonic() >= session.deadline` while the session is still `VERIFYING`, the host shall terminate the session with decision `DENY` and reason `TIMEOUT`, transmitting a deny command to the ESP32.
* **Owner:** `AccessController`.

### FR-013: Grant Actuation
* **Statement:** Only an explicit `ACCESS_GRANTED` command shall cause the ESP32 to actuate the door servo to the open position.
* **Specification:** Upon receiving a valid, authenticated-in-session `access_command` with `decision: "grant"`, the ESP32 shall generate a $50\text{ Hz}$ PWM pulse commanding the servo to the calibrated unlocked angle ($90^\circ$ or $180^\circ$).
* **Owner:** ESP32 Firmware.

### FR-014: Door Hold and Close
* **Statement:** Following an access grant, the ESP32 shall hold the door unlocked for a configured duration, then return it to the locked state.
* **Specification:** The door shall remain unlocked for `door_hold_ms` (default $3000\text{ ms}$, specified in the command payload). Once elapsed, the ESP32 shall reposition the servo to the locked position ($0^\circ$).
* **Owner:** ESP32 Firmware.

### FR-015: Denied Indication
* **Statement:** An access denial shall activate the red LED and produce a continuous long buzzer alert.
* **Specification:** Upon receiving `decision: "deny"`, the ESP32 shall illuminate the Red LED and sound the buzzer for $1500\text{ ms}$. The servo shall remain strictly in the locked position.
* **Owner:** ESP32 Firmware.

### FR-016: Granted Indication
* **Statement:** An access grant shall activate the green LED and produce a short beep.
* **Specification:** Concurrently with servo opening (`FR-013`), the ESP32 shall illuminate the Green LED for the duration of the door hold and emit two short audible beeps ($100\text{ ms}$ on, $100\text{ ms}$ off, $100\text{ ms}$ on).
* **Owner:** ESP32 Firmware.

### FR-017: Versioned Protocol
* **Statement:** All host-device communication shall use versioned Newline-Delimited JSON (NDJSON) messages.
* **Specification:** Every message transmitted in either direction shall contain protocol version integer `"v": 1`, a valid `"type"` string, and applicable correlation identifiers (`event_id`, `session_id`, `command_id`).
* **Owner:** `DeviceTransportPort` & Firmware Parser.

### FR-018: Command Acknowledgement
* **Statement:** The ESP32 shall acknowledge every received actuator command.
* **Specification:** Within $50\text{ ms}$ of receiving an `access_command`, the ESP32 shall transmit a `command_result` message echoing the `command_id` and reporting execution status (`executed`, `rejected`, or `error`).
* **Owner:** ESP32 Firmware.

### FR-019: Fail Closed
* **Statement:** Malformed, unknown, stale, duplicate, or unacknowledged commands shall never unlock the door.
* **Specification:** If the ESP32 receives an unparseable JSON string, an unknown message type, or a duplicate `command_id`, it shall reject the command, maintain the locked servo position, and log an error event.
* **Owner:** ESP32 Firmware & Host.

### FR-020: Enrollment
* **Statement:** The host shall provide an administrative CLI/routine to enroll new user identities, capture facial samples, train the LBPH model, and bind RFID UIDs.
* **Specification:** The enrollment workflow shall capture $\ge 10$ valid facial samples from the webcam, crop and normalize each sample, assign a unique integer `face_label`, train or update the `LBPHFaceRecognizer`, persist the model file, and store the `Person` and `RFIDCard` mappings in SQLite.
* **Owner:** `EnrollmentService`.

### FR-021: Access Logging
* **Statement:** Every access attempt shall be permanently logged with full audit telemetry.
* **Specification:** Each attempt shall record an `AccessEvent` containing: `event_id`, `session_id`, `timestamp` (ISO-8601 UTC), presented `card_uid`, `expected_person_id`, observed `recognized_person_id`, final `decision` (`GRANT` or `DENY`), and specific `reason_code`.
* **Owner:** `EventRepository`.

### FR-022: Model Persistence
* **Statement:** The trained LBPH facial model and label mappings shall be persisted locally and restored upon application restart.
* **Specification:** The OpenCV model shall be saved to disk as a YAML/XML file (`data/models/lbph.yml`), and label-to-person mappings shall be maintained in SQLite, enabling immediate operational readiness without retraining after reboot.
* **Owner:** `ModelStore` / `FileModelStore`.

### FR-023: Health State
* **Statement:** The host and ESP32 shall continuously track and expose component health to prevent operation during partial failures.
* **Specification:** The ESP32 shall emit periodic `heartbeat` messages (default every $1000\text{ ms}$). The host shall monitor heartbeat recency, camera availability, and database connectivity. If any subsystem is unhealthy, the host shall transition to state `FAULT` and refuse to process RFID events.
* **Owner:** `HealthService`.

### FR-024: Safe Recovery
* **Statement:** Following a power interruption, communication failure, or crash, physical outputs shall remain in or return to the safe locked state.
* **Specification:** Upon reboot or upon detecting serial link drop, the ESP32 shall immediately reset servo angle to $0^\circ$ and extinguish all indicator LEDs.
* **Owner:** ESP32 Firmware Watchdog.

### FR-025: Known Spoofing Limitation Disclosure
* **Statement:** System documentation and UI diagnostics shall explicitly state that printed 2D photographs and presentation attacks are not detected by this prototype.
* **Specification:** The project documentation must prominently feature this limitation, classifying DualKey as an educational prototype rather than a production biometric product.
* **Owner:** Documentation & System Architecture.
