# Comprehensive Test Case Catalog

**Document ID:** `DOC-06-CASES`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Test Case Specifications (`TEST-AUTH-001` through `TEST-AUTH-014`)

### TEST-AUTH-001: Correct RFID + Correct Face
* **Preconditions:** Person A enrolled with Card A (`UID_A`) and face model active.
* **Input:** Tap Card A; present Person A's face to webcam within $10.0\text{ s}$.
* **Expected Behavior:** Policy validates distance $\le \theta$ and matches $N \ge 3$ consecutive frames.
* **Hardware Output:** Green LED on; two short beeps; servo moves to $90^\circ$ (Open); holds $3\text{ s}$; returns to $0^\circ$ (Locked).
* **Audit Log:** `AccessEvent(decision='GRANT', reason='MATCHED_OWNER', card_uid='UID_A')`.
* **Pass/Fail:** PASS if door opens and returns to locked state safely.

### TEST-AUTH-002: Correct RFID + Wrong Face
* **Preconditions:** Person A enrolled with Card A; Person B enrolled with Card B.
* **Input:** Tap Card A; Person B presents face to webcam.
* **Expected Behavior:** LBPH recognizes Person B ($\ne$ Person A); triggers immediate rejection.
* **Hardware Output:** Servo remains locked ($0^\circ$); Red LED on; continuous long buzz ($1.5\text{ s}$).
* **Audit Log:** `AccessEvent(decision='DENY', reason='FACE_MISMATCH', expected='PersonA', observed='PersonB')`.
* **Pass/Fail:** PASS if door remains locked and denial alert fires.

### TEST-AUTH-003: Correct RFID + Unknown Face
* **Preconditions:** Person A enrolled with Card A. Unenrolled Person X presents face.
* **Input:** Tap Card A; Person X stands before camera.
* **Expected Behavior:** LBPH returns distance $> \theta$ (`LOW_CONFIDENCE`); scan continues until $10.0\text{ s}$ timeout.
* **Hardware Output:** Servo locked ($0^\circ$); at $T = 10.0\text{ s}$, Red LED on; long buzz.
* **Audit Log:** `AccessEvent(decision='DENY', reason='TIMEOUT')`.
* **Pass/Fail:** PASS if unknown face is never granted entry.

### TEST-AUTH-004: Unknown RFID
* **Preconditions:** System in `IDLE`. Card X not registered in database.
* **Input:** Tap Card X.
* **Expected Behavior:** Database query returns `None`; session not started; camera not activated.
* **Hardware Output:** Servo locked ($0^\circ$); Red LED on; long buzz.
* **Audit Log:** `AccessEvent(decision='DENY', reason='UNKNOWN_RFID', card_uid='UID_X')`.
* **Pass/Fail:** PASS if rejected immediately without engaging camera.

### TEST-AUTH-005: No Face Presented
* **Preconditions:** Person A enrolled with Card A.
* **Input:** Tap Card A; camera field of view remains empty.
* **Expected Behavior:** Face detector yields zero faces; session runs until monotonic deadline ($10.0\text{ s}$).
* **Hardware Output:** Servo locked ($0^\circ$); at $T = 10.0\text{ s}$, Red LED on; long buzz.
* **Audit Log:** `AccessEvent(decision='DENY', reason='TIMEOUT')`.
* **Pass/Fail:** PASS if timeout occurs accurately at 10.0s.

### TEST-AUTH-006: Timeout Boundary Test
* **Preconditions:** Person A enrolled with Card A.
* **Input:** Tap Card A; time monotonic clock steps across $T = 10.001\text{ s}$.
* **Expected Behavior:** Session transitions from `VERIFYING` to `TIMEOUT`.
* **Hardware Output:** Servo locked ($0^\circ$); Red LED on; long buzz.
* **Audit Log:** `AccessEvent(decision='DENY', reason='TIMEOUT')`.
* **Pass/Fail:** PASS if boundary triggers at $10.0\text{ s} \pm 50\text{ ms}$.

### TEST-AUTH-007: Face Presented After Timeout
* **Preconditions:** Person A enrolled with Card A.
* **Input:** Tap Card A; wait $10.5\text{ s}$; Person A steps into camera view.
* **Expected Behavior:** Session already terminated at $10.0\text{ s}$; late frames discarded.
* **Hardware Output:** Servo locked ($0^\circ$); no actuator reaction to late face.
* **Audit Log:** Timeout logged at $10.0\text{ s}$; zero grant events.
* **Pass/Fail:** PASS if late arrival receives zero grant.

### TEST-AUTH-008: Camera Failure
* **Preconditions:** Person A enrolled with Card A.
* **Input:** Tap Card A; unplug camera USB cable during `VERIFYING`.
* **Expected Behavior:** Camera read fails; system transitions to `FAULT`.
* **Hardware Output:** Servo locked ($0^\circ$); Red LED on.
* **Audit Log:** `AccessEvent(decision='DENY', reason='CAMERA_ERROR')`.
* **Pass/Fail:** PASS if system safely fails closed.

### TEST-AUTH-009: ESP32 Communication Failure
* **Preconditions:** System in `VERIFYING`.
* **Input:** Unplug USB serial cable between ESP32 and host.
* **Expected Behavior:** PySerial raises error; host cancels session; ESP32 watchdog closes door if open.
* **Hardware Output:** Servo remains or returns to $0^\circ$ (Locked).
* **Audit Log:** `AccessEvent(decision='DENY', reason='DEVICE_LINK_ERROR')`.
* **Pass/Fail:** PASS if physical lock is preserved.

### TEST-AUTH-010: Servo Failure / Actuator Timeout
* **Preconditions:** Grant issued; ESP32 commands servo.
* **Input:** Inject command acknowledgement failure from firmware simulator.
* **Expected Behavior:** Host logs `ACTUATOR_FAILURE`; enters safe state.
* **Hardware Output:** Default physical lock maintained.
* **Audit Log:** Diagnostic error logged with `reason='ACTUATOR_FAILURE'`.
* **Pass/Fail:** PASS if unacknowledged command is handled safely.

### TEST-AUTH-011: Multiple Faces in View
* **Preconditions:** Person A enrolled with Card A.
* **Input:** Tap Card A; two individuals look into camera simultaneously.
* **Expected Behavior:** Haar detector yields 2 bounding boxes; scene classified as ambiguous.
* **Hardware Output:** Servo locked ($0^\circ$); Red LED on; long buzz.
* **Audit Log:** `AccessEvent(decision='DENY', reason='MULTIPLE_FACES')`.
* **Pass/Fail:** PASS if multiple faces immediately deny access.

### TEST-AUTH-012: Printed Photograph Spoofing
* **Preconditions:** Person A enrolled with Card A.
* **Input:** Tap Card A; present 2D color photograph of Person A.
* **Expected Behavior:** Recognizer extracts LBPH texture; may grant access.
* **Hardware Output:** Green LED and servo may open.
* **Audit Log:** Event recorded; verified against documented limitation in `DOC-05-LIMIT`.
* **Pass/Fail:** PASS if behavior matches documented limitation and metric is recorded.

### TEST-AUTH-013: Enrollment Workflow
* **Preconditions:** Fresh database; camera active; unassigned Card A.
* **Input:** Run `python -m app.main --enroll`; enter "Alice"; tap Card A; capture 20 face samples.
* **Expected Behavior:** 20 normalized PNGs saved in `data/faces/<id>/`; model compiled to `lbph.yml`; SQLite updated.
* **Hardware Output:** Serial indicates card read; buzzer chirps on completion.
* **Audit Log:** Database contains active person and card record.
* **Pass/Fail:** PASS if newly enrolled user can immediately authenticate via `TEST-AUTH-001`.

### TEST-AUTH-014: Restart Recovery
* **Preconditions:** Database populated with enrolled users; model serialized on disk.
* **Input:** Terminate host process; reboot ESP32; restart host application.
* **Expected Behavior:** Database reloaded; `lbph.yml` read without retraining; ESP32 resumes heartbeat.
* **Hardware Output:** Servo initializes to $0^\circ$; LEDs off.
* **Audit Log:** System ready log emitted.
* **Pass/Fail:** PASS if complete system resumes operation without data loss.
