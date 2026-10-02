#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""DualKey Physical Hardware Diagnostic & Actuator Verification Utility.

Allows standalone testing of:
1. SG90 Micro Servo (0 degrees -> 90 degrees -> 0 degrees hold)
2. Status LEDs (Green grant indicator, Red denial indicator)
3. Buzzer (LEDC 2.7kHz PWM acoustic tone)
4. MFRC522 RFID reader real-time tag scan
"""

import argparse
import json
import sys
import time
import uuid

import serial


def send_command(ser: serial.Serial, decision: str, hold_ms: int = 3000) -> None:
    cmd_id = f"diag-{uuid.uuid4().hex[:8]}"
    msg = {
        "type": "access_command",
        "command_id": cmd_id,
        "session_id": f"sess-{cmd_id}",
        "decision": decision,
        "reason": "manual_hardware_test",
        "door_hold_ms": hold_ms,
    }
    payload = json.dumps(msg) + "\n"
    print(f"\n[HOST -> ESP32] Sending {decision.upper()} command: {payload.strip()}")
    ser.write(payload.encode("utf-8"))
    ser.flush()

    # Wait for execution acknowledgement
    deadline = time.time() + 4.5
    while time.time() < deadline:
        line = ser.readline().decode("utf-8", errors="ignore").strip()
        if not line:
            continue
        print(f"  [ESP32] {line}")
        if cmd_id in line:
            print(f"[OK] ESP32 executed {decision.upper()} successfully!")
            break


def main() -> None:
    parser = argparse.ArgumentParser(description="DualKey Hardware Diagnostic Tool")
    parser.add_argument(
        "--port", default="/dev/ttyUSB0", help="Serial port (default: /dev/ttyUSB0)"
    )
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    parser.add_argument(
        "--test",
        choices=["servo", "grant", "deny", "rfid", "all"],
        default="all",
        help="Test mode to execute",
    )
    args = parser.parse_args()

    print("=" * 65)
    print("DualKey ESP32 Hardware Diagnostic Tool")
    print(f"Connecting to {args.port} @ {args.baud} baud...")
    print("=" * 65)

    try:
        ser = serial.Serial(args.port, args.baud, timeout=0.5)
        time.sleep(1.5)  # Allow ESP32 serial reset settle
        ser.reset_input_buffer()
    except Exception as e:
        print(f"\n[ERROR] Could not open serial port {args.port}: {e}")
        print("Make sure no other process (like 'dualkey --run') is currently using the port.")
        sys.exit(1)

    try:
        if args.test in ("servo", "grant", "all"):
            print("\n>>> Testing Access GRANT Actuation:")
            print("    - SG90 Servo should rotate to 90 degrees (OPEN)")
            print("    - Green LED should light up")
            print("    - Buzzer should emit 2 short confirmation beeps")
            print("    - Door holds open for 3 seconds, then Servo locks back to 0 degrees")
            send_command(ser, "grant", hold_ms=3000)
            time.sleep(3.5)

        if args.test in ("deny", "all"):
            print("\n>>> Testing Access DENIAL Actuation:")
            print("    - SG90 Servo must STAY LOCKED at 0 degrees")
            print("    - Red LED should light up for 0.8s")
            print("    - Buzzer should emit solid denial buzz")
            send_command(ser, "deny", hold_ms=0)
            time.sleep(1.2)

        if args.test in ("rfid", "all"):
            print("\n>>> Testing MFRC522 RFID Reader:")
            print("    Tap any RFID card on the reader now (testing for 8 seconds)...")
            deadline = time.time() + 8.0
            found = False
            while time.time() < deadline:
                line = ser.readline().decode("utf-8", errors="ignore").strip()
                if "rfid_detected" in line:
                    try:
                        data = json.loads(line)
                        uid = data.get("uid")
                        ev_id = data.get("event_id")
                        print(f"    [DETECTED] Card UID: {uid} (Event: {ev_id})")
                        found = True
                    except Exception:
                        print(f"    [RAW] {line}")
            if not found:
                print("    [NOTE] No RFID card was tapped within 8 seconds.")

        print("\n" + "=" * 65)
        print("Diagnostic complete!")
        print("=" * 65)

    finally:
        ser.close()


if __name__ == "__main__":
    main()
