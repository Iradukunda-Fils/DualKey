# Security Boundaries & Trust Zones

**Document ID:** `DOC-05-BOUNDARIES`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Trust Zone Taxonomy

DualKey establishes three distinct trust zones across its physical and computational footprint:

```text
+--------------------------------------------------------------------------+
|  ZONE 0: UNTRUSTED EXTERIOR (Physical Entry Portal)                      |
|  - RFID Radio Frequency Field (Subject to cloning & sniffing)            |
|  - Optical Camera Field of View (Subject to photograph presentation)     |
+--------------------------------------------------------------------------+
                                    │
                         (Hardware Airgap / Lens)
                                    │
+-----------------------------------▼--------------------------------------+
|  ZONE 1: SEMI-TRUSTED SENSOR & ACTUATION PERIMETER (ESP32 Edge Device)   |
|  - Microcontroller firmware, GPIO logic, SPI lines, PWM signal           |
|  - Assumed: Firmware executes authentic binary without physical tap      |
|  - Limitation: No cryptographic hardware root of trust (no secure element)|
+--------------------------------------------------------------------------+
                                    │
                         (USB Serial Boundary)
                                    │
+-----------------------------------▼--------------------------------------+
|  ZONE 2: TRUSTED APPLICATION CORE (Host Workstation)                     |
|  - Python AccessController, AuthorizationPolicy                          |
|  - SQLite Database (app.db) & Trained Models (lbph.yml)                  |
|  - Linux OS User Process & Monotonic Clock                               |
+--------------------------------------------------------------------------+
```

---

## 2. Boundary Isolation Invariants

1. **The Host-to-Device Serial Seam:**
   * The ESP32 is treated as a dumb sensing and execution peripheral.
   * The host does not trust the ESP32 to make security decisions.
   * If the ESP32 firmware is compromised or corrupted, it cannot manufacture a cryptographic or database grant on the host. However, since the ESP32 directly controls the servo PWM pin, physical protection of the ESP32 enclosure is required to prevent direct pin manipulation.

2. **The Vision Processing Seam:**
   * Raw video frames from `/dev/video0` are untrusted data streams.
   * The `FaceDetector` and `FaceRecognizer` are data extraction pipelines; their outputs are treated purely as untrusted candidate observations until validated by the `AuthorizationPolicy`.

3. **Memory Isolation:**
   * Biometric facial embeddings and histograms reside exclusively within the host Python process heap and local filesystem. The ESP32 never receives, caches, or transmits biometric imagery or histograms.
