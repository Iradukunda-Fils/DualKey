# Physical Serial Interface & Protocol Specification

**Document ID:** `DOC-04-PROTO-PHYS`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Physical UART Channel Specification

The physical link between the host laptop and the ESP32 edge microcontroller operates over an integrated USB-to-UART bridge (CP2102, CH340, or FT232).

| Bus Property | Specification Value | Engineering Note |
| :--- | :--- | :--- |
| **Baud Rate** | $115200\text{ bps}$ | Standard ESP32 bootloader and runtime baud rate. |
| **Data Bits** | $8$ | Standard byte framing. |
| **Parity** | None | No parity bit. |
| **Stop Bits** | $1$ | Standard 8N1 serial framing. |
| **Flow Control** | None | Hardware RTS/CTS is disabled. Software XON/XOFF disabled. |
| **Framing** | Newline-Delimited (`\n`, `0x0A`) | ASCII line break separates discrete messages. |
| **Max Message Size**| $512\text{ bytes}$ | Prevents heap fragmentation on the ESP32 microcontroller. |

---

## 2. Boot & Handshake Sequence

When the USB serial cable is plugged into the laptop, the DTR/RTS signals toggle, causing an automatic hardware reset of the ESP32.

```text
[Laptop Host]                                      [ESP32 Microcontroller]
      │                                                      │
      │  (USB Connected / DTR Toggled)                       │
      ├─────────────────────────────────────────────────────>│ (Hardware Reset)
      │                                                      │ (Init Peripherals)
      │                                                      │ (Set Servo to 0 deg)
      │<─── {"v":1,"type":"heartbeat","state":"CLOSED"} ─────┤ (Boot Complete)
      │                                                      │
      ├─── Host arms listener ───────────────────────────────┤
```

1. **Firmware Reset:** ESP32 boots in $< 300\text{ ms}$. It initializes GPIOs, verifies MFRC522 communication over SPI, and commands the servo to the locked position ($0^\circ$).
2. **First Heartbeat:** The firmware emits its initial `heartbeat` message.
3. **Host Synchronization:** The host `HealthService` marks the transport healthy upon receipt of the first valid JSON heartbeat.

---

## 3. Heartbeat & Liveness Timing

* **Heartbeat Period:** The ESP32 transmits a `heartbeat` message every $1000\text{ ms}$ ($\pm 50\text{ ms}$).
* **Host Timeout:** If the host application does not receive a valid heartbeat within $3000\text{ ms}$ ($3 \times$ missed heartbeats), it transitions to state `FAULT` and rejects any pending access requests.
* **Firmware Link Loss Watchdog:** If the ESP32 receives an access grant but subsequently loses serial connectivity, its autonomous hardware hold timer ($3000\text{ ms}$) guarantees that the door will return to the locked position without requiring a host close command.
