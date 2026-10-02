# Ubiquitous Language & Engineering Glossary

**Document ID:** `DOC-00-GLOSSARY`  
**Status:** Approved Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Domain Terminology

To maintain conceptual integrity across requirements, architecture, firmware, computer vision, and tests, the following terms have strict, unambiguous meanings throughout DualKey.

| Term | Strict Definition |
| :--- | :--- |
| **Access Decision** | The final, immutable determination made exclusively by the laptop host's `AuthorizationPolicy`. Values: `GRANT`, `DENY`. |
| **Access Session** | A transient, stateful entity created upon the presentation of a valid RFID card. It binds the detected card, expected person, start timestamp, and a strict 10.0-second monotonic deadline. |
| **Card Owner** | The specific `Person` entity uniquely linked to an enrolled `RFIDCard` UID in the persistence layer. |
| **Fail-Closed** | The foundational safety principle dictating that in any indeterminate state, failure, error, timeout, or ambiguity, physical actuators remain or immediately return to the locked/closed position. |
| **Face Detection** | The algorithmic determination of whether one or more human faces exist in a camera frame, returning bounding box coordinates `(x, y, w, h)`. |
| **Face Recognition** | The algorithmic matching of a detected, cropped, and normalized face against enrolled facial biometric models, producing a candidate identity label and a statistical distance metric. |
| **Hold Interval** | The duration (default: 3000 ms) during which the door servo remains in the unlocked/open position following an `ACCESS_GRANTED` decision before automatically moving back to locked/closed. |
| **LBPH** | Local Binary Patterns Histograms. A texture-based facial feature extraction and classification algorithm implemented via OpenCV's `cv2.face.LBPHFaceRecognizer`. |
| **LBPH Distance** | The chi-square statistical distance computed between a test sample's histogram and an enrolled model's histogram. **Lower distance indicates higher confidence/similarity.** |
| **Monotonic Clock** | A continuous, monotonically non-decreasing clock (`time.monotonic()` in Python) unaffected by system clock steps, NTP adjustments, or daylight saving time changes. Mandatory for all session timing. |
| **NDJSON** | Newline-Delimited JSON. A stream framing format where each discrete protocol message is encoded as a valid JSON object followed immediately by a single newline character (`\n`). |
| **Presentation Attack** | An attempt to subvert the biometric recognizer using an artifact such as a printed paper photograph, tablet display, or 3D mask. |
| **Stable-Match Gate** | A safety filter requiring $N$ consecutive positive recognitions ($N \ge 3$) for the identical expected person within the verification window before granting access, filtering out transient misclassifications. |
| **Verification Window** | The strictly enforced 10.0-second time span commencing at the instant a valid RFID card is accepted by the host. |
| **UID** | Unique Identifier. The 4-byte or 7-byte serial number broadcast by an RFID transponder to the MFRC522 reader. Treated as an unauthenticated identifier in DualKey. |

---

## 2. Universal State Names

The access control state machine adheres to these exact names across all documentation, source code, and telemetry:

* `IDLE`: Resting state, waiting for RFID presentation. Servo is locked, LEDs off.
* `CARD_VALIDATING`: Transient state while host checks database for card UID validity.
* `VERIFYING`: Active 10-second window. Camera is capturing frames and evaluating faces.
* `GRANTED`: Positive authorization confirmed. Actuator is open, green LED lit, short beep emitted.
* `DENIED`: Explicit authorization failure (wrong card, wrong face, multiple faces, timeout). Red LED lit, long buzz emitted.
* `TIMEOUT`: Specific subcategory of denial occurring when 10.0 seconds elapse without positive match.
* `FAULT`: System safety state entered upon camera error, transport loss, or firmware panic. Fail-closed enforced.
