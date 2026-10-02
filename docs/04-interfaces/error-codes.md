# Error & Reason Code Catalog

**Document ID:** `DOC-04-CODES`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Universal Reason Code Taxonomy

DualKey rejects arbitrary free-form error messages in core workflows. Every authorization outcome, rejection, or error condition must be classified using a standardized, machine-readable reason code from this catalog.

| Reason Code String | Domain Category | Authorization Outcome | Hardware Actuation | Operational Explanation |
| :--- | :--- | :--- | :--- | :--- |
| **`MATCHED_OWNER`** | Success | `GRANT` | Servo Opens ($90^\circ$); Green LED on; 2 short beeps. | Full 2-factor binding validated with $N \ge 3$ stable matches. |
| **`MATCH_IN_PROGRESS`** | Transient | `CONTINUE` | None (Door remains locked). | Single positive frame recorded; awaiting stable match count ($< N$). |
| **`FACE_NOT_FOUND`** | Transient | `CONTINUE` | None (Door remains locked). | No human face detected in current frame; scan continues until 10s timeout. |
| **`LOW_CONFIDENCE`** | Transient | `CONTINUE` | None (Door remains locked). | Detected face distance exceeds calibrated threshold ($\chi^2 > \theta$). |
| **`UNKNOWN_RFID`** | Rejection | `DENY` | Servo locked; Red LED on; long buzz ($1.5\text{ s}$). | Presented RFID card UID is not enrolled or is marked inactive. |
| **`FACE_MISMATCH`** | Rejection | `DENY` | Servo locked; Red LED on; long buzz ($1.5\text{ s}$). | Recognized face matches an enrolled person who is NOT the card owner. |
| **`MULTIPLE_FACES`** | Rejection | `DENY` | Servo locked; Red LED on; long buzz ($1.5\text{ s}$). | Frame contains $> 1$ face; scene rejected for ambiguity. |
| **`TIMEOUT`** | Rejection | `DENY` | Servo locked; Red LED on; long buzz ($1.5\text{ s}$). | 10.0-second monotonic verification window elapsed without match. |
| **`CAMERA_ERROR`** | Fault | `DENY / FAULT` | Servo locked; Red LED on. | Video capture device disconnected or frame read returned `None`. |
| **`DEVICE_LINK_ERROR`**| Fault | `DENY / FAULT` | Servo locked; Fail-closed. | USB serial connection lost or heartbeat missed for $> 3.0\text{ s}$. |
| **`COMMAND_REJECTED`** | Fault | `DENY / FAULT` | Servo locked; Logged. | Microcontroller reported parse error or invalid command parameters. |
| **`ACTUATOR_FAILURE`** | Fault | `FAULT` | Servo locked; Logged. | Command acknowledgement timed out without execution confirmation. |

---

## 2. Python Enum Implementation (`app/domain/reason_codes.py`)

```python
from enum import Enum

class ReasonCode(str, Enum):
    MATCHED_OWNER = "MATCHED_OWNER"
    MATCH_IN_PROGRESS = "MATCH_IN_PROGRESS"
    FACE_NOT_FOUND = "FACE_NOT_FOUND"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    UNKNOWN_RFID = "UNKNOWN_RFID"
    FACE_MISMATCH = "FACE_MISMATCH"
    MULTIPLE_FACES = "MULTIPLE_FACES"
    TIMEOUT = "TIMEOUT"
    CAMERA_ERROR = "CAMERA_ERROR"
    DEVICE_LINK_ERROR = "DEVICE_LINK_ERROR"
    COMMAND_REJECTED = "COMMAND_REJECTED"
    ACTUATOR_FAILURE = "ACTUATOR_FAILURE"
```
