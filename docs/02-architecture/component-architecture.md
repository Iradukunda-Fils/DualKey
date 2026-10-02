# Component Architecture (C4 Level 3)

**Document ID:** `DOC-02-COMPONENT`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Host Application Component Model

The diagram below details the internal structure of the Python host application and its decomposition into domain, application, ports, and adapters.

```mermaid
classDiagram
    direction TB

    namespace Domain {
        class AccessSession {
            +str session_id
            +str card_uid
            +str expected_person_id
            +float started_at
            +float deadline
            +SessionState state
            +int match_count
            +is_active(now) bool
        }
        class AuthorizationPolicy {
            +evaluate(session, recognition, now, config) AccessDecision
        }
        class AccessDecision {
            +DecisionResult decision
            +ReasonCode reason
            +str session_id
            +str person_id
        }
        class Person {
            +str person_id
            +str display_name
            +int face_label
            +str status
        }
        class RFIDCard {
            +str uid
            +str person_id
            +str status
        }
    }

    namespace Application {
        class AccessController {
            -IdentityRepository identity_repo
            -EventRepository event_repo
            -CameraPort camera
            -FaceRecognizerPort recognizer
            -DeviceTransportPort transport
            -ClockPort clock
            -SystemConfig config
            -AccessSession active_session
            +process_tick() void
            +handle_rfid_event(event) void
        }
        class EnrollmentService {
            +enroll_person(name, card_uid, samples) str
        }
        class HealthService {
            +check_health() SystemHealth
        }
    }

    namespace Ports {
        class CameraPort {
            <<interface>>
            +open() void
            +read() Frame
            +close() void
        }
        class FaceRecognizerPort {
            <<interface>>
            +predict(face_gray) RecognitionResult
            +train(labeled_faces) void
            +save() void
            +load() void
        }
        class DeviceTransportPort {
            <<interface>>
            +send_access_command(command) void
            +poll() List~DeviceEvent~
            +health() TransportHealth
        }
        class IdentityRepository {
            <<interface>>
            +get_card_owner(uid) Person
            +get_person(person_id) Person
            +create_person(person) void
            +bind_card(uid, person_id) void
        }
    }

    AccessController --> AccessSession : manages
    AccessController --> AuthorizationPolicy : delegates
    AccessController --> CameraPort : uses
    AccessController --> FaceRecognizerPort : uses
    AccessController --> DeviceTransportPort : uses
    AccessController --> IdentityRepository : queries
    AuthorizationPolicy ..> AccessDecision : produces
```

---

## 2. Firmware Component Breakdown (ESP32)

The ESP32 firmware is divided into four modular subsystems coordinated by a deterministic main loop:

```text
firmware/
├── include/
│   ├── config.h            # Pin definitions, baud rates, timing constants
│   ├── protocol.h          # NDJSON message structs and ArduinoJson serializers
│   ├── rfid_subsystem.h    # MFRC522 SPI driver and debounce logic
│   ├── actuator_subsystem.h# SG90 PWM driver, LED togglers, Buzzer player
│   └── safety_watchdog.h   # Heartbeat emitter and link-loss fail-closed guard
└── src/
    └── main.cpp            # FreeRTOS / Arduino setup() and loop() orchestration
```

### Firmware Responsibilities

1. **`rfid_subsystem`:** Configures VSPI pins, polls `mfrc522.PICC_IsNewCardPresent()` and `mfrc522.PICC_ReadCardSerial()`, extracts hex UID string, and prevents rapid duplicate emissions via a $500\text{ ms}$ debounce lock.
2. **`actuator_subsystem`:** Binds ESP32 LEDC PWM channel to GPIO 25. Manages non-blocking state machine for door unlocking ($90^\circ$), holding ($3000\text{ ms}$), and relocking ($0^\circ$). Coordinates GPIO 26 (Green LED), GPIO 27 (Red LED), and GPIO 32 (Buzzer).
3. **`protocol`:** Deserializes incoming NDJSON lines from `Serial` into `AccessCommand` C++ structs using `ArduinoJson`. Serializes `RfidEvent`, `CommandResult`, and `Heartbeat` messages to `Serial`.
4. **`safety_watchdog`:** Emits periodic heartbeat every $1000\text{ ms}$. If the door is open and the hold timer expires, it forcibly closes the door even if no further host commands arrive.
