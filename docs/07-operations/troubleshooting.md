# Operational Troubleshooting & Diagnostic Guide

**Document ID:** `DOC-07-TROUBLE`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Quick Diagnostic Triage Table

| Symptom / Observed Behavior | Likely Root Cause | Diagnostic Check | Resolution Procedure |
| :--- | :--- | :--- | :--- |
| **ESP32 resets repeatedly (`RTCWDT_BROWN_OUT_RESET`)** | Servo motor drawing peak stall current from 3.3V logic rail. | Check ESP32 serial output at boot. Inspect servo $V_+$ wire. | Rewire servo to external $5\text{ V}$ power supply. Tie grounds together. |
| **RFID cards not detected at all** | SPI wiring error or MFRC522 connected to $5\text{ V}$ instead of $3.3\text{ V}$. | Verify SPI pin continuity (`GPIO 18, 19, 23, 5, 22`). Check reader red power LED. | Reconnect to $3.3\text{ V}$. If reader was attached to $5\text{ V}$, replace MFRC522 module. |
| **Host logs `PermissionError: [Errno 13] /dev/ttyUSB0`** | Current user lacks membership in `dialout` group. | Run `id -nG` to list user groups. | Execute `sudo usermod -a -G dialout $USER` and log back into desktop session. |
| **`cv2.VideoCapture(0)` fails to open** | Webcam occupied by another application or permissions missing. | Run `lsof /dev/video0` or `fuser /dev/video0`. | Close competing browser/conferencing apps. Add user to `video` group. |
| **Enrolled user repeatedly denied with `LOW_CONFIDENCE`** | Room lighting too dim or distance threshold too aggressive. | Inspect audit event log for recorded `distance` values. | Re-run calibration tool. Increase ambient illumination ($\ge 300\text{ lux}$). |
| **Host logs `DEVICE_LINK_ERROR` / missing heartbeat** | Loose USB cable or baud rate mismatch. | Verify serial baud is set to `115200` in both host `.env` and firmware `config.h`. | Secure USB cable. Inspect cable for data line capability (avoid charge-only cables). |

---

## 2. Hardware Self-Test Commands

### Verify Serial Stream Manually
```bash
picocom -b 115200 /dev/ttyUSB0
# Should see periodic heartbeat messages:
# {"v":1,"type":"heartbeat","device_id":"door-01","payload":{"state":"CLOSED"...}}
```

### Verify Webcam Feed
```bash
v4l2-ctl --list-devices
ffplay /dev/video0
```
