# ADR-0003: ESP32 Owns Physical Sensing & Actuation

**Document ID:** `ADR-0003`  
**Status:** Accepted  
**Date:** September 29, 2026  
**Deciders:** Lead Software Architect, Systems Engineer, Embedded Engineer  

---

## 1. Context & Problem Statement

DualKey requires low-level interfacing with an MFRC522 SPI RFID reader, an SG90 PWM servo motor, status LEDs, and an audible buzzer. We must decide whether to control these components via an external microcontroller or attempt direct GPIO manipulation from the laptop host (e.g. via USB-to-GPIO FTDI adapters).

---

## 2. Decision

The **ESP32 microcontroller is designated the sole owner of physical peripheral I/O**. The laptop host never manipulates hardware GPIO or PWM pins directly.

---

## 3. Rationale

1. **Deterministic Timing:** Generating clean $50\text{ Hz}$ PWM pulses for servo control requires microsecond-level timing precision, which an ESP32 hardware timer (`LEDC`) handles deterministically without jitter. Non-real-time Linux host kernels are prone to scheduling delays that cause servo chatter.
2. **SPI Protocol Execution:** Interfacing with the MFRC522 requires rapid polling and SPI register transactions suited for a bare-metal microcontroller loop.
3. **Autonomous Failsafe:** In the event of host lockup or USB cable severance while the door is unlocked, the ESP32 maintains an independent internal hardware timer to safely return the servo to $0^\circ$ (locked).

---

## 4. Consequences

### Positive
* Perfect PWM stability and jitter-free servo motion.
* Complete physical safety isolation; host crashes cannot hold hardware open.
* Standardized, portable laptop software with zero board-specific GPIO dependencies.

### Negative / Trade-offs
* Requires maintaining two separate codebases (Python host and C++ firmware).
