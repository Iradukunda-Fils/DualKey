# High-Level System Design (HLD)

**Document ID:** `DOC-02-HLD`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Architectural Layers & Responsibilities

DualKey organizes its host software into clean architectural layers, enforcing strict separation of concerns and unidirectional dependencies toward the inner domain.

```text
+--------------------------------------------------------------------------+
|  DOMAIN LAYER (Pure Business Logic & State)                              |
|  - Models: Person, RFIDCard, AccessSession, AccessDecision, ReasonCode   |
|  - Policy: AuthorizationPolicy (Pure evaluation function)                |
+--------------------------------------------------------------------------+
                                    ▲
                                    │ (Invoked by)
+--------------------------------------------------------------------------+
|  APPLICATION LAYER (Orchestration & Use Cases)                           |
|  - AccessController (Session lifecycle, monotonic timer, event router)   |
|  - EnrollmentService (User onboarding, sample acquisition, training)     |
|  - HealthService (Component watchdog, status reporting)                  |
|  - EventLogger (Audit record construction)                               |
+--------------------------------------------------------------------------+
                                    │
                                    ▼ (Communicates via)
+--------------------------------------------------------------------------+
|  PORTS / INTERFACES (Abstract Contracts)                                 |
|  - CameraPort, FaceRecognizerPort, DeviceTransportPort                   |
|  - IdentityRepository, EventRepository, ModelStore, ClockPort            |
+--------------------------------------------------------------------------+
                                    ▲
                                    │ (Implemented by)
+--------------------------------------------------------------------------+
|  ADAPTERS (Infrastructure & Concrete Drivers)                            |
|  - OpenCVCameraAdapter (UVC webcam capture via cv2.VideoCapture)         |
|  - OpenCVLBPHAdapter (Haar detection, preprocessing, LBPH inference)     |
|  - Esp32SerialAdapter (PySerial NDJSON framing & correlation)            |
|  - SqliteIdentityRepository (SQLite 3 relational queries)                |
|  - FileModelStore (Local disk YAML/XML model serialization)              |
|  - MonotonicClock (time.monotonic wrapper)                               |
+--------------------------------------------------------------------------+
                                    │
                                    ▼ (Physical Serial Link)
+--------------------------------------------------------------------------+
|  EMBEDDED FIRMWARE LAYER (ESP32 C++)                                     |
|  - MFRC522 SPI Poller, NDJSON Serial Parser / Formatter                  |
|  - SG90 Servo PWM Driver, LED & Buzzer Indicators, Safe-State Watchdog   |
+--------------------------------------------------------------------------+
```

### Layer Responsibility Matrix

| Layer | Primary Responsibilities | Strict Invariants ("Must Not Do") |
| :--- | :--- | :--- |
| **Domain** | Holds immutable data models, session state objects, reason codes, and the pure `AuthorizationPolicy`. | **Must not** import `cv2`, `serial`, `sqlite3`, `RPi.GPIO`, or perform filesystem I/O. |
| **Application** | Orchestrates access workflows, tracks the 10.0s monotonic deadline, calls ports, coordinates enrollment. | **Must not** manipulate low-level hardware bits or execute direct SQL queries. |
| **Ports** | Declares structural typing interfaces (`typing.Protocol`) for all external dependencies. | **Must not** contain concrete implementation logic or external package imports. |
| **Adapters** | Bridges external libraries (OpenCV, PySerial, SQLite) to Port interfaces. | **Must not** make autonomous authorization decisions or modify domain policy rules. |
| **Firmware** | Interacts with MFRC522 SPI, drives PWM/GPIO, parses/formats NDJSON, maintains hardware safe state. | **Must not** perform face recognition, evaluate identity binding, or bypass host decisions. |

---

## 2. Runtime Interaction Walkthrough

1. **Card Presentation:** An RFID card approaches the MFRC522 antenna. The ESP32 firmware reads the card UID via SPI.
2. **Serial Event Emission:** The ESP32 formats an `rfid_detected` message and transmits it over USB UART to the laptop.
3. **Identity Resolution:** The host `AccessController` intercepts the event and queries the `IdentityRepository` for the UID.
4. **Session Instantiation:** If valid, an `AccessSession` is created with `state = VERIFYING` and `deadline = time.monotonic() + 10.0`.
5. **Frame Acquisition:** While `state == VERIFYING`, `CameraPort.read()` fetches video frames.
6. **Biometric Evaluation:** The face pipeline detects faces. If exactly one face is found, `FaceRecognizerPort.predict()` returns `(label, distance)`.
7. **Policy Decision:** `AuthorizationPolicy.evaluate()` checks distance $\le \text{threshold}$, identity match, and increments `match_count`.
8. **Grant Actuation:** Once $N = 3$ consecutive matches occur, an `access_command` with `decision: "grant"` is dispatched to the ESP32.
9. **Physical Execution:** The ESP32 executes the command, unlocking the servo for $3000\text{ ms}$, lighting the Green LED, and returning `command_result`.
10. **Audit Logging:** The `EventLogger` writes an immutable audit record to SQLite and closes the session back to `IDLE`.

---

## 3. Failure Handling Matrix

| Failure Mode | Host Action | ESP32 Device Action | Final Outcome |
| :--- | :--- | :--- | :--- |
| **Unknown RFID UID** | Rejects immediately with reason `UNKNOWN_RFID`; logs event. | Remains closed; illuminates Red LED + long buzz. | `ACCESS_DENIED` |
| **No Face Detected in 10s** | Scans continuously until `deadline`; terminates with `TIMEOUT`. | Remains closed; illuminates Red LED + long buzz. | `ACCESS_DENIED` |
| **Wrong Enrolled Face** | Detects mismatch; terminates immediately with `FACE_MISMATCH`. | Remains closed; illuminates Red LED + long buzz. | `ACCESS_DENIED` |
| **Multiple Faces in View** | Evaluates scene as ambiguous; terminates with `MULTIPLE_FACES`. | Remains closed; illuminates Red LED + long buzz. | `ACCESS_DENIED` |
| **Sub-Threshold Distance** | Treats as `LOW_CONFIDENCE`; continues scanning until deadline. | Remains closed; no output change until timeout. | `ACCESS_DENIED` |
| **Camera Failure / Unplug** | Enters `FAULT` state; terminates active session; logs error. | Remains closed; autonomous watchdog maintains lock. | `FAULT / CLOSED` |
| **Serial Link Disconnection** | Aborts active session; logs `DEVICE_LINK_ERROR`. | Automatically times out and resets servo to locked. | `FAULT / CLOSED` |
| **Malformed JSON Command** | Logs parse error; discards frame. | Rejects message with `command_result: "error"`; stays locked. | `REJECTED / CLOSED` |
| **Duplicate Command ID** | Discards duplicate command. | Ignores duplicate `command_id`; maintains current state. | `SAFE IDEMPOTENCY` |
| **Hardware Reboot / Panic** | Reinitializes repositories; waits for new device heartbeat. | Hardware reset forces servo to $0^\circ$ and clears outputs. | `SAFE RECOVERY` |

---

## 4. Scalability Seams Architecture

The architecture maintains clear seams for future growth without adding premature complexity:

```text
Today (MVP Local Prototype):
[Host Policy Core] ──> [Esp32SerialAdapter] ──> [USB Serial] ──> [Single ESP32 Door]

Future Evolution Seam (Zero Core Policy Changes):
[Host Policy Core] ──> [DeviceGatewayAdapter] ──> [TLS / TCP / MQTT] ──> [Door Registry (N Doors)]

Today (Local Machine Learning):
[Host Policy Core] ──> [OpenCVLBPHAdapter] ──> [Local CPU Inference]

Future Evolution Seam:
[Host Policy Core] ──> [InsightFaceONNXAdapter] ──> [Edge TPU / NPU Accelerator]
```
