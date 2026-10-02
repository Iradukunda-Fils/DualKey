# Engineering Assumptions & Technical Constraints

**Document ID:** `DOC-00-CONSTRAINTS`  
**Status:** Approved Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. System Assumptions

1. **Physical Proximity:** The RFID reader and camera are co-located at the physical entry point. The user presenting the RFID card is facing the camera at an approximate distance of 0.4 to 1.0 meters.
2. **Ambient Lighting:** The operational environment has reasonably consistent ambient indoor illumination (approximately 200–500 lux). LBPH is sensitive to dramatic lighting shifts and deep directional shadows.
3. **Dedicated Host Process:** The laptop host runs DualKey as a high-priority foreground application or dedicated local service with unimpeded access to `/dev/video0` and `/dev/ttyUSB0`.
4. **Single-User Access Sequence:** Individuals approach the access point serially (one person at a time).
5. **Trusted Local Host:** The operating system, memory space, and USB communication bus on the laptop are assumed secure from local malicious compromise for the purposes of this prototype.

---

## 2. Hardware Constraints & Lifecycle Notices

### 2.1 MFRC522 RFID Reader IC
* **Lifecycle Notice:** NXP lists the MFRC522 family as End of Life (EOL) / Not Recommended for New Designs (NRND). It is accepted strictly as an educational prototype component. It must not be specified for commercial production designs without architectural review and migration to contemporary secure reader ICs (e.g., NXP CLRC663 or PN5180).
* **Operating Voltage:** $2.5\text{ V} - 3.6\text{ V}$ (Nominal $3.3\text{ V}$). Connecting the MFRC522 $V_{CC}$ pin to the $5\text{ V}$ rail will permanently damage the silicon.
* **Bus Interface:** Serial Peripheral Interface (SPI) up to $10\text{ MHz}$.

### 2.2 SG90 Micro Servo Motor & Electrical Power Integrity
* **Voltage & Current:** Operates on $4.8\text{ V} - 6.0\text{ V}$. Stall current can reach $500\text{ mA} - 800\text{ mA}$.
* **Power Isolation Mandate:** **The servo must never be powered directly from the ESP32 onboard 3.3V LDO regulator.** Doing so causes severe $V_{DD}$ rail brownouts, triggering ESP32 brownout detector resets (`RTCWDT_BROWN_OUT_RESET`). The servo requires an independent $5\text{ V}$ external power supply or a decoupled USB $5\text{ V}$ tap with common ground tied to the ESP32 ground pin.
* **Control Signal:** $50\text{ Hz}$ PWM ($20\text{ ms}$ period), pulse width approximately $0.5\text{ ms}$ ($0^\circ$, locked) to $2.5\text{ ms}$ ($180^\circ$, unlocked). Exact calibration angles are marked as `TBD` pending mechanical mounting assembly.

### 2.3 ESP32 Microcontroller (NodeMCU / DevKit v1)
* **Logic Level:** $3.3\text{ V}$ CMOS. Inputs are not $5\text{ V}$ tolerant.
* **Strapping Pins:** Care must be taken to avoid GPIO strapping conflicts:
  * `GPIO 0`: Bootloader mode selection (pull-up required for normal boot).
  * `GPIO 2`: Flashing status (must be floating/low during boot).
  * `GPIO 12` (MTDI): Flash voltage selection (must be low on boot for $3.3\text{ V}$ SPI flash).
  * `GPIO 15` (MTDO): UART output silence (must be pulled high).
* Pin assignments chosen in the Low-Level Design (LLD) avoid these strapping pins.

### 2.4 Laptop Webcam
* **Resolution & Frame Rate:** Nominal $640 \times 480$ resolution at $\ge 15\text{ FPS}$.
* **Interface:** Standard USB Video Class (UVC) accessible via OpenCV `cv2.VideoCapture(0)`.

---

## 3. Operational Constraints

1. **Local Connectivity Only:** The host communicates with the ESP32 over a single point-to-point USB CDC Serial link. No network routers, Wi-Fi access points, or cloud gateways are permitted in the MVP.
2. **Fixed 10-Second Window:** The verification window is fixed at 10.0 seconds. It cannot be extended arbitrarily by continuous camera presence.
3. **Threshold Calibration Required:** The LBPH distance threshold cannot be globally hardcoded. It is subject to empirical calibration on the deployed hardware setup (marked as `TBD` during initial deployment until calibration is executed).
