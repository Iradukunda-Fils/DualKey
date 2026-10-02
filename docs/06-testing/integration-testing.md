# Integration Testing Specification

**Document ID:** `DOC-06-INTEGRATION`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Test Harness Architecture

DualKey utilizes specialized mock adapters to execute integration tests of the full `AccessController` loop without requiring physical serial cables or physical webcams.

```text
[Pytest Integration Test Runner]
                │
                ▼
      [AccessController]
        ├── IdentityRepository ────> [In-Memory SQLite: ':memory:']
        ├── EventRepository ───────> [In-Memory SQLite: ':memory:']
        ├── ClockPort ─────────────> [SimulatedClock (Monotonic Stepper)]
        ├── CameraPort ────────────> [MockCameraAdapter (Synthetic Frame Feeder)]
        └── DeviceTransportPort ───> [SimulatedSerialAdapter (Queue-based ESP32 Sim)]
```

---

## 2. Mock Adapter Contracts

### 2.1 `SimulatedSerialAdapter`
Maintains an in-memory queue of incoming and outgoing NDJSON messages. Emulates the ESP32 state machine, returning `command_result(executed)` when an `access_command` is received.

### 2.2 `MockCameraAdapter`
Yields a predefined sequence of synthetic frames (e.g., 3 frames containing Person A's face, followed by frames with no face). Enables precise testing of the Stable-Match Gate and frame processing loops.

---

## 3. Integration Scenarios

| Test ID | Workflow Tested | Sequence of Events | Verification Assertion |
| :--- | :--- | :--- | :--- |
| `TEST-INT-001` | Full Access Grant | 1. Emit `rfid_detected("CARD_A")`.<br/>2. Step clock $100\text{ ms}$.<br/>3. Mock camera yields 3 consecutive Person A frames. | `transport.last_command.decision == "grant"`. Audit event recorded in DB. |
| `TEST-INT-002` | Immediate Mismatch Denial | 1. Emit `rfid_detected("CARD_A")`.<br/>2. Mock camera yields Person B frame. | `transport.last_command.decision == "deny"`. Session terminated immediately. |
| `TEST-INT-003` | Timeout Expiration | 1. Emit `rfid_detected("CARD_A")`.<br/>2. Mock camera yields empty frames.<br/>3. Advance simulated clock by $10.1\text{ s}$. | `transport.last_command.decision == "deny"` with `reason="TIMEOUT"`. |
| `TEST-INT-004` | Camera Disconnect During Verifying | 1. Emit `rfid_detected("CARD_A")`.<br/>2. Set mock camera state to disconnected. | Controller enters `FAULT`. Stays closed. |
