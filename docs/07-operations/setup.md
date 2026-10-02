# Hardware Assembly & Setup Guide

**Document ID:** `DOC-07-SETUP`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Required Components Bill of Materials (BOM)

| Item | Component Description | Quantity | Purpose |
| :--- | :--- | :--- | :--- |
| 1 | ESP32 DevKit v1 (30-pin or 38-pin) | 1 | Microcontroller edge device agent. |
| 2 | NXP MFRC522 13.56 MHz RFID Module | 1 | RFID card transponder reader. |
| 3 | MIFARE Classic 1K / NTAG RFID Cards/Fobs | 2+ | Physical possession factor tokens. |
| 4 | TowerPro SG90 9g Micro Servo Motor | 1 | Door latch actuation simulator. |
| 5 | Green 5mm LED | 1 | Access granted visual indicator. |
| 6 | Red 5mm LED | 1 | Access denied / error visual indicator. |
| 7 | Active 5V Buzzer | 1 | Audible feedback alert sounder. |
| 8 | $330\,\Omega$ Resistors (1/4W) | 2 | Current limiters for LEDs. |
| 9 | External 5V Regulated Power Supply (or 5V UBEC) | 1 | Isolated servo motor power. |
| 10 | Solderless Breadboard & Jumper Wires | 1 set | Physical circuit prototyping. |
| 11 | Laptop with Integrated/USB Webcam & Linux OS | 1 | Host computer-vision and authorization brain. |

---

## 2. Step-by-Step Wiring Instructions

```text
[ESP32]                  [MFRC522 RFID]
3V3   ───────────────────> VCC (DO NOT USE 5V!)
GND   ───────────────────> GND
GPIO 22 ─────────────────> RST
GPIO 5  ─────────────────> SDA / SS
GPIO 18 ─────────────────> SCK
GPIO 19 ─────────────────> MISO
GPIO 23 ─────────────────> MOSI

[ESP32]                  [INDICATORS]
GPIO 26 ─── [ 330 ohm ] ──> Green LED Anode ──> Cathode ──> GND
GPIO 27 ─── [ 330 ohm ] ──> Red LED Anode   ──> Cathode ──> GND
GPIO 32 ─────────────────> Buzzer (+)       ──> (-)     ──> GND

[ESP32]                  [SERVO SG90]
GPIO 25 ─────────────────> PWM Signal (Orange/Yellow Wire)
GND    ────────┬────────> Ground (Brown Wire)
               │
[External 5V]  │
GND    ────────┘ (Common Ground Tied Together)
+5V    ──────────────────> Power (Red Wire)
```

> [!CAUTION]
> **Check Connections Before Applying Power:**
> 1. Verify the MFRC522 $V_{CC}$ wire is firmly on the ESP32 $3.3\text{ V}$ pin. A $5\text{ V}$ connection will fry the reader IC.
> 2. Ensure external $5\text{ V}$ power ground is tied to ESP32 GND. Floating grounds cause servo jitter and PWM signal corruption.
