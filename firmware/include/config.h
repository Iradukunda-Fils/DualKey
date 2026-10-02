// SPDX-License-Identifier: MIT
// DualKey ESP32 Firmware — Hardware Pin Map & Timing Constants
//
// Reference: DOC-03-HW (docs/03-design/hardware-control.md)
//
// PHYSICAL HARDWARE WIRING DIRECTORY & REVIEW:
// ==============================================================================
// 1. MFRC522 RFID Reader (SPI Protocol - 3.3V Logic):
//    - 3.3V  -> ESP32 3V3 Pin (CRITICAL: DO NOT CONNECT TO 5V!)
//    - RST   -> ESP32 GPIO 22 (Software Reset)
//    - GND   -> ESP32 GND (Common Ground)
//    - IRQ   -> UNCONNECTED (Unused interrupt pin)
//    - MISO  -> ESP32 GPIO 19 (Master In Slave Out)
//    - MOSI  -> ESP32 GPIO 23 (Master Out Slave In)
//    - SCK   -> ESP32 GPIO 18 (SPI Clock)
//    - SDA   -> ESP32 GPIO 5  (Chip Select / SS)
//
// 2. SG90 Micro Servo Motor (LEDC 50Hz PWM):
//    - Yellow/Orange -> ESP32 GPIO 25 (PWM Control Signal)
//    - Red           -> External +5V Power Rail (or 5V supply)
//    - Chocolate/Brown -> GND (Common Ground tied to ESP32 GND)
//
// 3. Status Indicators:
//    - Green LED Anode (+) -> ESP32 GPIO 26 (via 330 ohm resistor) -> GND
//    - Red LED Anode (+)   -> ESP32 GPIO 27 (via 330 ohm resistor) -> GND
//    - Active Buzzer (+)   -> ESP32 GPIO 32 -> GND
//
// 4. USB Serial CDC / UART Protocol:
//    - USB Port: /dev/ttyUSB0 or /dev/ttyACM0 @ 115200 Baud (8N1)
// ==============================================================================

#ifndef DUALKEY_CONFIG_H
#define DUALKEY_CONFIG_H

// ── SPI RFID (MFRC522) Pin Configuration ───────────────────────────
#define RFID_SCK_PIN   18  // Hardware SPI Clock Pin
#define RFID_MISO_PIN  19  // Hardware SPI MISO Pin
#define RFID_MOSI_PIN  23  // Hardware SPI MOSI Pin
#define RFID_CS_PIN     5  // Hardware SPI Slave Select (SDA)
#define RFID_RST_PIN   22  // Hardware Reset Control Pin

// ── Servo PWM (SG90) Pin & PWM Duty Cycle Settings ─────────────────
// CRITICAL: Servo motor must draw current from 5V supply, NEVER ESP32 3.3V regulator
#define SERVO_PIN      25  // GPIO 25 attached to SG90 Yellow signal wire
#define SERVO_CHANNEL   0  // ESP32 LEDC PWM channel 0
#define SERVO_FREQ     50  // 50 Hz PWM frequency (20ms total period)
#define SERVO_RESOLUTION 16 // 16-bit PWM resolution (0 to 65535 duty values)

// Duty Cycle Calculations for 16-bit @ 50Hz (20ms period = 65535 total units):
//   0 degrees (Locked): 0.5ms pulse -> (0.5 / 20.0) * 65535 = 1638
//  90 degrees (Open):   1.5ms pulse -> (1.5 / 20.0) * 65535 = 4915
// 180 degrees (Max):    2.5ms pulse -> (2.5 / 20.0) * 65535 = 8192
#define SERVO_LOCKED    1638  // Duty cycle for 0 degrees (door locked)
#define SERVO_OPEN      4915  // Duty cycle for 90 degrees (door open)

// ── Status Indicator LED Pins ───────────────────────────────────────
#define GREEN_LED_PIN  26  // Access Granted indicator pin (GPIO 26)
#define RED_LED_PIN    27  // Access Denied / Error indicator pin (GPIO 27)

// ── Audible Feedback Buzzer Pin & PWM Configuration ─────────────────
#define BUZZER_PIN       32  // Buzzer pin (GPIO 32)
#define BUZZER_CHANNEL    1  // ESP32 LEDC PWM channel 1 (independent from Servo on channel 0)
#define BUZZER_FREQ    2700  // 2.7 kHz resonant tone for piezo/passive buzzers
#define BUZZER_RES        8  // 8-bit PWM resolution (0-255)

// ── Serial Link & Timing Constants ───────────────────────────────────
#ifndef SERIAL_BAUD
#define SERIAL_BAUD      115200 // Serial communication speed matching Python host
#endif

#ifndef RFID_POLL_INTERVAL_MS
#define RFID_POLL_INTERVAL_MS   50 // Fast 50ms (20 Hz) polling for instant card detection
#endif

#ifndef DOOR_HOLD_MS
#define DOOR_HOLD_MS     3000 // Default door open hold duration (3.0 seconds)
#endif

#ifndef DENY_BUZZ_MS
#define DENY_BUZZ_MS      800 // Access denied red LED & buzzer duration (0.8s for snappy recovery)
#endif

#define HEARTBEAT_INTERVAL_MS  1000 // Send heartbeat telemetry every 1.0 second

// ── NDJSON Message Protocol Limits ───────────────────────────────────
#define MAX_JSON_FRAME_BYTES  512 // Maximum NDJSON line buffer length
#define PROTOCOL_VERSION       1 // Protocol schema version identifier

#endif // DUALKEY_CONFIG_H
