# Hardware-in-the-Loop (HIL) Testing Specification

**Document ID:** `DOC-06-HIL`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Physical Test Setup Checklist

Before initiating Hardware-in-the-Loop (HIL) tests, the test operator must verify the physical bench setup:

- [ ] **MFRC522 Voltage Rail:** Verified connected to ESP32 $3.3\text{ V}$ pin (NOT $5\text{ V}$).
- [ ] **Servo Motor Power:** Verified connected to decoupled external $5\text{ V}$ power supply.
- [ ] **Common Ground:** Verified that ESP32 GND and external $5\text{ V}$ PSU ground are bridged together.
- [ ] **Current-Limiting Resistors:** $330\,\Omega$ resistors present in series with Green and Red LEDs.
- [ ] **USB Connection:** Shielded USB cable connected to laptop; `/dev/ttyUSB0` or `/dev/ttyACM0` enumerates cleanly in `dmesg`.
- [ ] **Webcam Positioning:** Laptop webcam positioned at eye level, $0.5\text{ m} - 0.8\text{ m}$ from the user, with ambient indoor light ($\approx 300\text{ lux}$).

---

## 2. Hardware Bring-Up Sequence

Execute in order before running full application suites:

```text
[Step 1: Serial Link Echo]
  Flash minimal firmware to ESP32 -> Verify heartbeat messages in screen/minicom at 115200 baud.
       │
       ▼
[Step 2: SPI RFID Reader Check]
  Tap enrolled test card -> Verify hex UID string printed cleanly in UART terminal without parity errors.
       │
       ▼
[Step 3: Actuator Sweep Test]
  Run firmware diagnostic mode:
  - Servo sweeps 0 deg -> 90 deg -> 0 deg.
  - Green LED toggles. Red LED toggles.
  - Buzzer emits test chirp.
       │
       ▼
[Step 4: End-to-End Application Launch]
  Launch python -m app.main -> Execute Acceptance Test Battery ACC-001..ACC-010.
```

---

## 3. Physical Observation Log Template

Each HIL run must be logged with physical observations:

| Parameter | Observed Value | Expected Benchmark | Pass / Fail |
| :--- | :--- | :--- | :--- |
| **Servo Latch Travel** | Angle measured mechanically: $90^\circ \pm 5^\circ$ | Full unlatching of simulated deadbolt. | PASS / FAIL |
| **Servo Hold Interval** | Measured via digital stopwatch: $3.0\text{ s} \pm 0.2\text{ s}$ | $3000\text{ ms}$ specified in command payload. | PASS / FAIL |
| **Buzzer Deny Alert** | Audible continuous tone for $1.5\text{ s}$ | Distinct warning buzz on denial. | PASS / FAIL |
| **Brownout Behavior** | ESP32 `uptime_ms` continues without resetting during servo actuation | No resets (`RTCWDT_BROWN_OUT_RESET`). | PASS / FAIL |
