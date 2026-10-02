# End-to-End Data Flow & Sequence Models

**Document ID:** `DOC-02-FLOW`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Sequence Diagram: Authorized Access Flow (Happy Path)

The sequence diagram below details the exact message choreography between the user, hardware, firmware, and host application during a successful authorization sequence.

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Cardholder
    participant Reader as MFRC522 (SPI)
    participant FW as ESP32 Firmware
    participant Transport as Serial Transport
    participant Host as AccessController
    participant DB as SQLite Repo
    participant Cam as Laptop Webcam
    participant Recog as LBPH Recognizer
    participant Actuator as Servo & Indicators

    User->>Reader: Tap RFID Card
    Reader->>FW: Detect Card & Read UID (e.g. "A1B2C3D4")
    FW->>Transport: Emit NDJSON {"type":"rfid_detected","uid":"A1B2C3D4"}
    Transport->>Host: Dispatch RfidDetectedEvent
    Host->>DB: Query get_card_owner("A1B2C3D4")
    DB-->>Host: Return Person(id="P01", name="Alice", label=1)
    Host->>Host: Start Session (state=VERIFYING, deadline=now+10.0s)
    
    loop Frame Acquisition & Evaluation (up to 10s)
        Host->>Cam: read()
        Cam-->>Host: Video Frame (640x480)
        Host->>Recog: Detect & Predict (face_gray)
        Recog-->>Host: RecognitionResult(label=1, distance=42.5)
        Host->>Host: Evaluate Policy: distance <= 65 AND label == P01
        Host->>Host: Increment match_count (1 -> 2 -> 3)
    end

    Note over Host: Stable-match gate satisfied (count=3 >= 3)
    Host->>DB: Record AccessEvent(decision="GRANT", reason="MATCHED_OWNER")
    Host->>Transport: Send access_command(decision="grant", door_hold_ms=3000)
    Transport->>FW: Parse NDJSON access_command
    FW->>Actuator: Rotate Servo to 90 deg (OPEN)
    FW->>Actuator: Turn on Green LED + 2 Short Beeps
    FW->>Transport: Emit command_result(status="executed")
    
    Note over FW,Actuator: Door remains open for 3000 ms
    FW->>Actuator: Rotate Servo to 0 deg (LOCKED)
    FW->>Actuator: Turn off Green LED
    FW->>Transport: Emit heartbeat(state="CLOSED")
```

---

## 2. Sequence Diagram: Biometric Mismatch Flow (Wrong Face)

```mermaid
sequenceDiagram
    autonumber
    actor Attacker as Attacker with Stolen Card
    participant FW as ESP32 Firmware
    participant Host as AccessController
    participant DB as SQLite Repo
    participant Cam as Laptop Webcam
    participant Recog as LBPH Recognizer
    participant Actuator as Servo & Indicators

    Attacker->>FW: Tap Stolen Card (Owner: Alice, ID: "P01")
    FW->>Host: Emit rfid_detected("A1B2C3D4")
    Host->>DB: get_card_owner("A1B2C3D4") -> Returns Alice ("P01")
    Host->>Host: Start Session (state=VERIFYING, expected="P01")
    
    Host->>Cam: read()
    Cam-->>Host: Frame containing Attacker's face (Bob)
    Host->>Recog: Predict face
    Recog-->>Host: RecognitionResult(label=2, distance=38.0) [Bob, ID: "P02"]
    
    Note over Host: Mismatch detected! (observed "P02" != expected "P01")
    Host->>DB: Record AccessEvent(decision="DENY", reason="FACE_MISMATCH")
    Host->>FW: Send access_command(decision="deny", reason="FACE_MISMATCH")
    FW->>Actuator: Keep Servo at 0 deg (LOCKED)
    FW->>Actuator: Turn on Red LED + Long Buzz (1500 ms)
    FW->>Actuator: Turn off Red LED
    Host->>Host: Terminate Session (state=IDLE)
```

---

## 3. Sequence Diagram: 10-Second Window Expiration Flow (Timeout)

```mermaid
sequenceDiagram
    autonumber
    actor User as Cardholder (Steps Away)
    participant FW as ESP32 Firmware
    participant Host as AccessController
    participant Cam as Laptop Webcam
    participant Actuator as Servo & Indicators

    User->>FW: Tap Card A
    FW->>Host: Emit rfid_detected("A1B2C3D4")
    Host->>Host: Start Session (deadline = T_0 + 10.0s)
    
    loop While monotonic_time < deadline
        Host->>Cam: read()
        Note over Host: Zero faces detected or distance > threshold
    end

    Note over Host: Clock reaches T_0 + 10.001s (Deadline Exceeded)
    Host->>FW: Send access_command(decision="deny", reason="TIMEOUT")
    FW->>Actuator: Keep Servo at 0 deg (LOCKED)
    FW->>Actuator: Turn on Red LED + Long Buzz (1500 ms)
    Host->>Host: Terminate Session (state=IDLE)
```
