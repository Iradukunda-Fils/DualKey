# Failure Modes & Fail-Closed Recovery

**Document ID:** `DOC-05-RECOVERY`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Fail-Closed Posture

The absolute invariant across all failure scenarios is **Fail-Closed**: Under no circumstances does a failure, error, or unhandled exception cause the physical door latch to release or remain open.

```text
Any Error / Exception / Loss of Signal
                  │
                  ▼
         [Enter Safe State]
                  │
     ┌────────────┴────────────┐
     ▼                         ▼
[Host Application]     [ESP32 Firmware]
- Cancel active session- Force servo angle to 0 deg
- Transition to FAULT  - Extinguish Green LED
- Refuse new RFID cards- Reset hold timer to 0
- Log diagnostic event - Maintain lock indefinitely
```

---

## 2. Failure Recovery Scenarios

| Failure Event | Detection Mechanism | Immediate System Response | Recovery Procedure |
| :--- | :--- | :--- | :--- |
| **Complete Power Loss** | Hardware blackout. | SG90 servo loses power. Mechanical spring or friction holds latch in locked position. | Upon power restoration, ESP32 bootloader sets PWM to $0.5\text{ ms}$ ($0^\circ$). Host reboots into `IDLE`. |
| **USB Serial Disconnect** | PySerial raises `SerialException`; ESP32 misses host polling. | Host marks `TransportHealth.DOWN`, enters `FAULT`. ESP32 non-blocking hold timer closes door if open, returns to `IDLE`. | Re-insert USB cable. Host auto-reconnects and waits for `heartbeat`. |
| **Webcam Unplugged** | `cv2.VideoCapture.read()` returns `None`. | Active session immediately denied with `reason="CAMERA_ERROR"`. Host transitions to `FAULT`. | Re-insert webcam. Host diagnostic loop reopens device handle. |
| **Malformed Command Injected**| ArduinoJson returns `DeserializationError`. | ESP32 discards buffer, logs error to UART, and maintains $0^\circ$ servo lock. | Host receives rejection or timeout; logs `COMMAND_REJECTED`. |
| **Host Process Crash** | Process termination (SIGTERM, SIGKILL, unhandled exception). | ESP32 detects lack of host commands. FreeRTOS loop maintains locked state. | Host watchdog or systemd service manager restarts `dualkey-host`. |
