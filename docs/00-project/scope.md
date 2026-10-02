# Project Scope & Boundary Management

**Document ID:** `DOC-00-SCOPE`  
**Status:** Approved Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. System Boundary Definition

DualKey is deliberately bounded to prove two-factor identity binding on a minimal physical and computational footprint. The system boundary comprises exactly one physical door mock-up, one ESP32 controller, one RFID sensor, one webcam, and one local laptop host.

```text
[ IN-SCOPE BOUNDARY ]
+--------------------------------------------------------------------------+
|  Laptop Host                                                             |
|  - Python Core (Domain Policy, Session Manager, SQLite Repository)       |
|  - Computer Vision (OpenCV Haar Cascade + LBPH Face Recognizer)          |
|  - Local USB Serial Device Adapter                                       |
|                                                                          |
|         ▲                                         ▲                      |
|         │ USB Serial (NDJSON)                     │ USB Video (UVC)      |
|         ▼                                         ▼                      |
|                                                                          |
|  ESP32 Microcontroller                            Laptop Webcam          |
|  - MFRC522 SPI RFID Reader                                               |
|  - SG90 Servo Actuator (Door Lock Simulation)                            |
|  - Green LED, Red LED, Active Buzzer                                     |
+--------------------------------------------------------------------------+
                                     │
                             (Physical Airgap)
                                     │
                                     ▼
[ EXPLICITLY OUT OF SCOPE ]
- Cloud APIs, Remote Identity Providers, Kubernetes, Distributed DBs
- Liveness detection, Anti-spoofing, Thermal/IR imaging
- Multi-door synchronization, Mobile app, High-assurance smart cards
```

---

## 2. In-Scope vs. Explicitly Out-of-Scope

| Functional Area | In Scope (MVP Baseline) | Explicitly Out of Scope (Non-Goals) | Rationale & Architectural Rule |
| :--- | :--- | :--- | :--- |
| **Physical Deployment** | 1 Door, 1 ESP32, 1 MFRC522, 1 Webcam, 1 Laptop Host. | Multi-door installations, distributed building controllers, turnstiles, magnetic locks. | Avoid premature distributed system complexity. Boundary seams exist via `DeviceTransportPort`. |
| **User Population** | Small enrolled set (typically 1 to 5 identities for prototype demo). | Enterprise directories, thousands of users, LDAP/Active Directory synchronization. | Small local SQLite and local YAML/XML model stores are fully sufficient. |
| **RFID Technology** | MFRC522 13.56 MHz reading 4-byte / 7-byte card UIDs in cleartext. | Cryptographically authenticated smart cards (MIFARE DESFire EV2/EV3, iCLASS, AES SAM). | The MVP validates possession factor binding, not RF credential tamper-resistance. |
| **Biometric Vision** | OpenCV Haar Cascade detector + Local Binary Patterns Histograms (LBPH). | Deep neural networks (FaceNet, InsightFace), cloud vision APIs, GPU acceleration pipelines. | LBPH is deterministic, runs in real-time on CPU, requires minimal training samples, and has zero external cloud dependencies. |
| **Biometric Anti-Spoofing** | Explicit documentation of spoofing limitation. | Liveness detection, blink detection, texture frequency analysis, 3D structured light, IR cameras. | Liveness detection is a distinct, complex engineering field beyond the educational MVP baseline. |
| **System Host / OS** | Linux / POSIX compatible laptop host (Ubuntu/Debian tested). | Windows native services, macOS daemons, container orchestration (Docker/K8s). | Direct access to `/dev/ttyUSB0` or `/dev/ttyACM0` and `/dev/video0` without virtualization friction. |
| **Communication** | USB Serial CDC at 115200 baud with Newline-Delimited JSON (NDJSON). | MQTT, WebSockets, Bluetooth Low Energy (BLE), Wi-Fi, Ethernet, gRPC. | USB serial provides deterministic latency, zero network config, and physical coupling for the prototype. |
| **Persistence** | Embedded SQLite 3 database and local file system (`faces/`, `models/`). | PostgreSQL, MySQL, Redis, DynamoDB, MongoDB, Cloud Object Storage (S3). | Eliminates external daemon dependencies and ensures completely offline operation. |

---

## 3. Explicit Non-Goals

1. **Production Security Guarantee:** This system is not designed to protect life, property, or classified assets. It is a systems-engineering proof-of-concept.
2. **Replay/Cloning Resistance on RF Channel:** Card UIDs are treated as identifiers, not cryptographic proofs. A cloned card presents the same UID as an authentic card.
3. **Photo Spoofing Protection:** The LBPH model operates on 2D texture patterns and can be fooled by printed photographs or mobile screen displays of an enrolled user.
4. **Autonomous Embedded Vision:** The ESP32 does not run computer vision models or process image frames.
5. **Direct Host Actuation:** The laptop host does not connect directly to GPIO pins or servo motor control lines.
