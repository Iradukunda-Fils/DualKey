# Hardware Requirements Specification

**Document ID:** `DOC-01-HW`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Overview

This document specifies the physical, electrical, and interface requirements for all hardware components comprising the DualKey prototype.

---

## 2. Requirement Specifications

### HW-001: Microcontroller Platform
* **Component:** Espressif ESP32 DevKit v1 (30-pin or 38-pin package, Xtensa dual-core 32-bit LX6 microprocessor).
* **Operating Logic:** $3.3\text{ V}$ CMOS.
* **Firmware Runtime:** C++ compiled under PlatformIO or Arduino ESP32 core v2.0+.
* **Hardware UART:** Hardware UART0 utilized for USB CDC serial communication with the laptop host at $115200\text{ baud}$, 8 data bits, no parity, 1 stop bit (8N1).

### HW-002: RFID Reader Subsystem
* **Component:** NXP MFRC522 Contactless Reader/Writer IC module.
* **Frequency:** $13.56\text{ MHz}$ ISM band, supporting ISO/IEC 14443 Type A transponders.
* **Supply Voltage:** Nominal $3.3\text{ V}$ ($2.5\text{ V} - 3.6\text{ V}$). **Caution:** Connection to $5\text{ V}$ rail prohibited.
* **Bus Interface:** Hardware SPI (VSPI or HSPI default bus):
  * `SCK`: GPIO 18
  * `MISO`: GPIO 19
  * `MOSI`: GPIO 23
  * `SDA / SS`: GPIO 5 (Chip Select)
  * `RST`: GPIO 22 (Hard Reset)

### HW-003: Actuator Subsystem (Door Lock Simulation)
* **Component:** TowerPro SG90 (or compatible) $9\text{g}$ Micro Servo Motor.
* **Operating Voltage:** $4.8\text{ V} - 6.0\text{ V}$ DC.
* **Power Supply Isolation:** The servo motor power ($V_+$, Red Wire) **must be supplied from an external 5V regulated source or a decoupled 5V USB power bus**, not the ESP32 $3.3\text{ V}$ LDO pin. Common ground (GND) must be tied directly between the external power supply and the ESP32.
* **Control Signal:** PWM signal driven from ESP32 GPIO 25 via the LEDC peripheral at $50\text{ Hz}$ ($20\text{ ms}$ period).
  * Locked Position: Nominal $0.5\text{ ms}$ pulse width ($0^\circ$).
  * Unlocked Position: Nominal $1.5\text{ ms} - 2.5\text{ ms}$ pulse width ($90^\circ$ to $180^\circ$, calibrated mechanically).

### HW-004: Visual & Audible Indicator Subsystem
* **Green LED (Grant Indicator):** Driven from GPIO 26 through a $330\,\Omega$ current-limiting resistor ($I_F \approx 5\text{ mA}$).
* **Red LED (Deny/Fault Indicator):** Driven from GPIO 27 through a $330\,\Omega$ current-limiting resistor ($I_F \approx 5\text{ mA}$).
* **Active Buzzer (Audible Alert):** Driven from GPIO 32. If driving an active buzzer drawing $> 12\text{ mA}$, an NPN switching transistor (e.g., 2N2222) with a flyback diode or base resistor must be utilized.

### HW-005: Host Interface Link
* **Physical Layer:** USB 2.0 Full-Speed connection via onboard USB-UART bridge (Silicon Labs CP2102, WCH CH340, or FTDI).
* **Baud Rate:** Fixed at $115200\text{ bps}$.
* **Cable:** Shielded USB Type-A to Micro-USB / Type-C cable ensuring steady $5\text{ V}$ power delivery.

### HW-006: Computer Vision Sensor
* **Component:** Laptop integrated webcam or external UVC-compliant USB webcam.
* **Format:** USB Video Class (UVC), uncompressed YUYV or MJPEG stream.
* **Performance:** $\ge 640 \times 480$ pixel resolution at a minimum of $15\text{ FPS}$ under ambient indoor lighting conditions.
