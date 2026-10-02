# Host-Device Communication Architecture

**Document ID:** `DOC-03-COMM`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Physical & Framing Layer

DualKey uses a local, full-duplex UART communication channel over USB CDC.

* **Baud Rate:** $115200\text{ bps}$ ($8$ data bits, no parity, $1$ stop bit — 8N1).
* **Framing Format:** Newline-Delimited JSON (NDJSON). Each frame consists of a single-line ASCII UTF-8 encoded JSON object terminated strictly by a single ASCII LF character (`\n`, `0x0A`).
* **Frame Size Limit:** Maximum frame length is 512 bytes, guaranteeing safe buffering within embedded ESP32 memory constraints.

```text
[Host Application]                               [ESP32 Firmware]
       │                                                │
       ├─── NDJSON Message + '\n' (Max 512B) ──────────>│ (UART RX Ring Buffer)
       │                                                │
       │<── NDJSON Message + '\n' (Max 512B) ───────────┤ (UART TX Buffer)
```

---

## 2. Message Envelope Specification

Every protocol transmission in either direction must adhere to the standardized top-level envelope schema:

```json
{
  "v": 1,
  "type": "rfid_detected | access_command | command_result | heartbeat",
  "event_id": "evt-uuid-string",
  "session_id": "sess-uuid-string",
  "command_id": "cmd-uuid-string",
  "device_id": "door-01",
  "payload": {}
}
```

### Correlation Field Invariants

| Field | Invariant & Purpose | Required Context |
| :--- | :--- | :--- |
| `"v"` | Protocol version integer (Must be `1`). | All messages. |
| `"type"` | Canonical message type string. | All messages. |
| `"event_id"` | Unique UUIDv4 assigned by the sender for each discrete hardware event. | Events originating from ESP32 (`rfid_detected`). |
| `"session_id"` | Correlation identifier linking an active host access verification session. | `access_command` and corresponding `command_result`. |
| `"command_id"` | Unique UUIDv4 assigned by the host for each actuator command. | `access_command` and echoed in `command_result`. |
| `"device_id"` | Logical identifier of the edge controller (default `"door-01"`). | All device emissions. |
| `"payload"` | Nested JSON object containing message-specific parameters. | All messages. |

---

## 3. Host Polling & Event Processing Model

To avoid multi-threaded race conditions and GIL contention during computer vision processing, the host application manages serial communication via a non-blocking cooperative polling architecture within `Esp32SerialAdapter`:

```python
class Esp32SerialAdapter:
    def __init__(self, port: str, baudrate: int = 115200):
        self._serial = serial.Serial(port, baudrate, timeout=0)
        self._rx_buffer = bytearray()

    def poll(self) -> list[DeviceEvent]:
        """Reads available bytes from UART and parses complete NDJSON lines."""
        events: list[DeviceEvent] = []
        waiting_bytes = self._serial.in_waiting
        if waiting_bytes > 0:
            chunk = self._serial.read(waiting_bytes)
            self._rx_buffer.extend(chunk)

            while b"\n" in self._rx_buffer:
                line, self._rx_buffer = self._rx_buffer.split(b"\n", 1)
                line = line.strip()
                if line:
                    event = self._parse_line(line.decode("utf-8", errors="replace"))
                    if event:
                        events.append(event)
        return events
```

---

## 4. Idempotency & Replay Defense

1. **Host-Side Tracking:** When an `access_command` is transmitted, the host registers the `command_id` and tracks it until a matching `command_result` arrives or a $500\text{ ms}$ command timeout elapses.
2. **Firmware-Side Deduplication:** The ESP32 maintains `char last_executed_command_id[37]` in static memory. If an incoming `access_command` contains an identical `command_id`, the firmware returns `result: "executed"` immediately without triggering another mechanical actuation.
