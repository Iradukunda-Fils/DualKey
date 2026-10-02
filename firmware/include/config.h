// SPDX-License-Identifier: MIT
// DualKey ESP32 Firmware — Hardware Pin Map & Timing Constants
//
// Reference: DOC-03-HW (docs/03-design/hardware-control.md)

#ifndef DUALKEY_CONFIG_H
#define DUALKEY_CONFIG_H

// ── SPI RFID (MFRC522) ─────────────────────────────────────────────
#define RFID_SCK_PIN   18
#define RFID_MISO_PIN  19
#define RFID_MOSI_PIN  23
#define RFID_CS_PIN     5
#define RFID_RST_PIN   22

// ── Servo PWM (SG90) ───────────────────────────────────────────────
// CRITICAL: Servo must be on external 5V supply, NEVER on ESP32 3.3V LDO
#define SERVO_PIN      25
#define SERVO_CHANNEL   0       // LEDC channel
#define SERVO_FREQ     50       // 50 Hz for standard servos
#define SERVO_RESOLUTION 16     // 16-bit resolution
// Pulse width calculations for 16-bit @ 50Hz:
//   0 deg = 0.5ms → 0.5/20 * 65535 = 1638
//  90 deg = 1.5ms → 1.5/20 * 65535 = 4915
// 180 deg = 2.5ms → 2.5/20 * 65535 = 8192
#define SERVO_LOCKED    1638    // 0 degrees (locked)
#define SERVO_OPEN      4915    // 90 degrees (open)

// ── Indicator LEDs ──────────────────────────────────────────────────
#define GREEN_LED_PIN  26       // Access granted indicator (330 ohm)
#define RED_LED_PIN    27       // Access denied indicator (330 ohm)

// ── Buzzer ──────────────────────────────────────────────────────────
#define BUZZER_PIN     32

// ── Timing Constants ────────────────────────────────────────────────
#ifndef SERIAL_BAUD
#define SERIAL_BAUD      115200
#endif

#ifndef RFID_POLL_INTERVAL_MS
#define RFID_POLL_INTERVAL_MS  200
#endif

#ifndef DOOR_HOLD_MS
#define DOOR_HOLD_MS     3000   // Default hold time for granted access
#endif

#ifndef DENY_BUZZ_MS
#define DENY_BUZZ_MS     1500   // Denial alert duration
#endif

#define HEARTBEAT_INTERVAL_MS  1000

// ── NDJSON Protocol ─────────────────────────────────────────────────
#define MAX_JSON_FRAME_BYTES  512
#define PROTOCOL_VERSION       1

#endif // DUALKEY_CONFIG_H
