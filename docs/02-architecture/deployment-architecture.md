# Deployment Architecture & Hardware Topology

**Document ID:** `DOC-02-DEPLOY`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Physical Deployment Topology

DualKey deploys as a cohesive edge-and-host setup. The laptop host resides inside the secure perimeter (e.g., inside an office or control station), while the ESP32 sensor/actuator head is positioned at the entry portal.

```text
+--------------------------------------------------------------------------+
|  SECURE / CONTROL ZONE (Laptop Host)                                     |
|                                                                          |
|  +--------------------------------------------------------------------+  |
|  |  Laptop Workstation (Linux OS / Python 3.10+)                      |  |
|  |  - Process: dualkey-host (PID: xxxx)                               |  |
|  |  - Persistence: /var/lib/dualkey/app.db (SQLite 3 WAL)             |  |
|  |  - Models: /var/lib/dualkey/models/lbph.yml                        |  |
|  |  - Samples: /var/lib/dualkey/faces/<person_id>/                    |  |
|  +-----------------------------------+--------------------------------+  |
|                                      │                                   |
+--------------------------------------|-----------------------------------+
                                       │
                USB 2.0 Cable (5V Bus / Data)
                (/dev/ttyUSB0 or /dev/ttyACM0)
                                       │
+--------------------------------------▼-----------------------------------+
|  PORTAL / ENTRYWAY PERIMETER (Edge Sensing & Actuation)                  |
|                                                                          |
|  +--------------------------------------------------------------------+  |
|  |  Integrated Laptop / External USB Webcam (/dev/video0)             |  |
|  +--------------------------------------------------------------------+  |
|                                                                          |
|  +--------------------------------------------------------------------+  |
|  |  ESP32 DevKit v1 Microcontroller                                   |  |
|  |  - Firmware: FreeRTOS / Arduino DualKey Device Agent               |  |
|  |  - 3.3V Logic Rail                                                 |  |
|  +---+---------------+---------------+---------------+----------------+  |
|      │ (SPI Bus)     │ (PWM GPIO 25) │ (GPIO 26/27)  │ (GPIO 32)         |
|      ▼               ▼               ▼               ▼                   |
|  +-------+       +-------+       +-------+       +--------+              |
|  |MFRC522|       | SG90  |       |LEDs   |       | Active |              |
|  |RFID   |       | Servo |       |Red &  |       | Buzzer |              |
|  |Reader |       | Latch |       |Green  |       | Sounder|              |
|  +-------+       +-------+       +-------+       +--------+              |
|      ▲               ▲                                                   |
|      │ (3.3V Only)   │ (External 5V Decoupled Rail)                      |
|  +---+---------------+------------------------------------------------+  |
|  | External 5V Regulated Power Supply (Decoupled GND tied to ESP32)   |  |
|  +--------------------------------------------------------------------+  |
+--------------------------------------------------------------------------+
```

---

## 2. Power Distribution & Grounding Mandate

```text
External 5V PSU (+5V) ───────────────> Servo SG90 Power (Red Wire)
External 5V PSU (GND) ───┬───────────> Servo SG90 Ground (Brown Wire)
                         │
                         └───────────> ESP32 DevKit GND Pin (Common Ground)

USB 5V Bus (from Laptop) ────────────> ESP32 VIN / V5 Pin
ESP32 3.3V LDO Output ───────────────> MFRC522 VCC Pin (3.3V ONLY)
ESP32 GND Pin ───────────────────────> MFRC522 GND Pin
```

> [!CAUTION]
> **Ground Loop & Brownout Prevention:**
> 1. Connecting the SG90 servo motor $V_+$ pin to the ESP32 $3.3\text{ V}$ pin will instantly collapse the microcontroller's logic voltage rail whenever the motor moves, causing an immediate brownout reboot.
> 2. Connecting the MFRC522 $V_{CC}$ pin to $5\text{ V}$ will destroy the RFID IC.
> 3. The ground (GND) of the external $5\text{ V}$ supply and the ground of the ESP32 **must be bridged together** to ensure a common reference for the PWM signal on GPIO 25.

---

## 3. Host Process Model

The host application runs as a single cooperative process utilizing a deterministic event-polling loop:

```text
[Main Process Thread]
       │
       ├── 1. Poll DeviceTransportAdapter (non-blocking read from serial buffer)
       ├── 2. Process incoming DeviceEvents (dispatch RFID events to session manager)
       ├── 3. If session is VERIFYING:
       │       ├── Check monotonic deadline (timeout evaluation)
       │       ├── Acquire frame from CameraPort
       │       ├── Execute Haar face detection
       │       ├── If 1 face: execute LBPH prediction
       │       └── Evaluate AuthorizationPolicy
       ├── 4. If decision reached: dispatch command to ESP32 via transport
       ├── 5. Check HealthService (heartbeat timeouts & error counters)
       └── 6. Sleep nominal 5ms to avoid CPU starvation
```
