# Architecture Decision Records (ADRs)

**Document ID:** `DOC-08-INDEX`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Purpose of ADRs

Architecture Decision Records (ADRs) document significant technical and architectural choices made throughout the DualKey engineering lifecycle. Each record captures the architectural context, decision taken, status, consequences, and compliance requirements.

---

## 2. ADR Log

| ADR ID | Title | Status | Date | Primary Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **`ADR-0001`** | [Documentation-First Engineering](file:///home/iradukunda/Lost/Learn/Auca-Innovation/IoT/DualKey/docs/08-decisions/ADR-0001-documentation-first.md) | **Accepted** | 2026-09-29 | Establish requirements, contracts, and testing baselines before writing code. |
| **`ADR-0002`** | [Laptop Host Owns Face Recognition](file:///home/iradukunda/Lost/Learn/Auca-Innovation/IoT/DualKey/docs/08-decisions/ADR-0002-laptop-owns-face-recognition.md) | **Accepted** | 2026-09-29 | Microcontroller compute/RAM limits; laptop webcam provides sufficient CPU/UVC pipeline. |
| **`ADR-0003`** | [ESP32 Owns Physical Sensing & Actuation](file:///home/iradukunda/Lost/Learn/Auca-Innovation/IoT/DualKey/docs/08-decisions/ADR-0003-esp32-owns-hardware-io.md) | **Accepted** | 2026-09-29 | Direct hardware GPIO, SPI, and PWM timing belong on a deterministic MCU. |
| **`ADR-0004`** | [OpenCV LBPH Selected for MVP Biometrics](file:///home/iradukunda/Lost/Learn/Auca-Innovation/IoT/DualKey/docs/08-decisions/ADR-0004-lbph-selected-for-mvp.md) | **Accepted** | 2026-09-29 | Deterministic, local, runs on CPU, rapid training, zero external cloud dependencies. |
| **`ADR-0005`** | [Local SQLite & File Persistence Selected](file:///home/iradukunda/Lost/Learn/Auca-Innovation/IoT/DualKey/docs/08-decisions/ADR-0005-local-persistence-selected.md) | **Accepted** | 2026-09-29 | Avoid cloud/network DB overhead for single-door local deployment. |
| **`ADR-0006`** | [NDJSON over USB Serial Protocol Selected](file:///home/iradukunda/Lost/Learn/Auca-Innovation/IoT/DualKey/docs/08-decisions/ADR-0006-communication-protocol-selected.md) | **Accepted** | 2026-09-29 | Human-readable, structured, versioned, easily debugged, robust frame delineation. |
| **`ADR-0007`** | [Pluggable Open-Source Face Recognition Strategy](file:///home/iradukunda/Lost/Learn/Auca-Innovation/IoT/DualKey/docs/08-decisions/ADR-0007-pluggable-face-recognition-strategy.md) | **Accepted** | 2026-09-29 | LBPH baseline, optional SFace/YuNet modern backend, prototype matching without fine-tuning. |
