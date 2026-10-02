// SPDX-License-Identifier: MIT
// DualKey ESP32 Firmware — Main Controller
//
// Non-blocking event loop implementing the firmware FSM:
//   DEVICE_STARTUP → CLOSED_SAFE → IDLE → OPENING → OPEN_HOLD → CLOSING → IDLE
//                                       → DENY_INDICATION → IDLE
//
// Reference: DOC-02-STATE (docs/02-architecture/state-machine.md)
//            DOC-03-HW   (docs/03-design/hardware-control.md)

#include <Arduino.h>
#include <SPI.h>
#include <MFRC522.h>
#include "config.h"
#include "protocol.h"

// ── Firmware State Machine ──────────────────────────────────────────

enum class DeviceState {
    DEVICE_STARTUP,
    CLOSED_SAFE,
    IDLE,
    OPENING,
    OPEN_HOLD,
    CLOSING,
    DENY_INDICATION
};

static DeviceState g_state = DeviceState::DEVICE_STARTUP;

// ── Hardware Instances ──────────────────────────────────────────────

static MFRC522 g_rfid(RFID_CS_PIN, RFID_RST_PIN);

// ── Timing State ────────────────────────────────────────────────────

static unsigned long g_lastRfidPoll    = 0;
static unsigned long g_lastHeartbeat   = 0;
static unsigned long g_actionStartMs   = 0;
static int           g_currentHoldMs   = DOOR_HOLD_MS;
static String        g_lastExecutedId  = "";

// ── Event Counter (for unique event IDs) ────────────────────────────

static unsigned long g_eventCounter = 0;

// ── Forward Declarations ────────────────────────────────────────────

void initHardware();
void setServoLocked();
void setServoOpen();
void clearIndicators();
void setGrantIndicators();
void setDenyIndicators();
void pollRfid();
void processSerialInput();
void handleAccessCommand(const AccessCommand& cmd);
void sendEventId(const String& uid);

// ── Setup ───────────────────────────────────────────────────────────

void setup() {
    Serial.begin(SERIAL_BAUD);
    while (!Serial) { delay(10); }
    Serial.setTimeout(20);

    initHardware();

    // Transition: DEVICE_STARTUP → CLOSED_SAFE
    setServoLocked();
    clearIndicators();
    g_state = DeviceState::CLOSED_SAFE;

    // Initialize MFRC522 RFID Reader with maximum antenna sensitivity
    SPI.begin(RFID_SCK_PIN, RFID_MISO_PIN, RFID_MOSI_PIN, RFID_CS_PIN);
    g_rfid.PCD_Init();
    delay(20);
    g_rfid.PCD_SetAntennaGain(g_rfid.RxGain_max);
    g_state = DeviceState::IDLE;
}

// ── Main Loop ───────────────────────────────────────────────────────

void loop() {
    unsigned long now = millis();

    // Heartbeat telemetry (always, regardless of state)
    if (now - g_lastHeartbeat >= HEARTBEAT_INTERVAL_MS) {
        g_lastHeartbeat = now;
        sendHeartbeat(now);
    }

    // Process incoming serial commands (always)
    processSerialInput();

    // State-specific behavior
    switch (g_state) {
        case DeviceState::IDLE:
            // Poll RFID at configured interval
            if (now - g_lastRfidPoll >= RFID_POLL_INTERVAL_MS) {
                g_lastRfidPoll = now;
                pollRfid();
            }
            break;

        case DeviceState::OPENING:
            // Servo is moving to open position
            setServoOpen();
            g_state = DeviceState::OPEN_HOLD;
            g_actionStartMs = now;
            break;

        case DeviceState::OPEN_HOLD:
            // Hold door open for configured duration
            // Autonomous timer: does NOT rely on host command to close
            if (now - g_actionStartMs >= (unsigned long)g_currentHoldMs) {
                g_state = DeviceState::CLOSING;
            }
            break;

        case DeviceState::CLOSING:
            setServoLocked();
            clearIndicators();
            g_state = DeviceState::IDLE;
            break;

        case DeviceState::DENY_INDICATION:
            // Red LED + buzzer for denial duration
            if (now - g_actionStartMs >= DENY_BUZZ_MS) {
                clearIndicators();
                g_state = DeviceState::IDLE;
            }
            break;

        case DeviceState::CLOSED_SAFE:
            // Stuck in safe mode until reset or self-test passes
            break;

        case DeviceState::DEVICE_STARTUP:
            // Should not reach here after setup()
            break;
    }
}

// ── Hardware Initialization ─────────────────────────────────────────

void initHardware() {
    // Servo PWM via LEDC
    ledcSetup(SERVO_CHANNEL, SERVO_FREQ, SERVO_RESOLUTION);
    ledcAttachPin(SERVO_PIN, SERVO_CHANNEL);

    // Indicator LEDs
    pinMode(GREEN_LED_PIN, OUTPUT);
    pinMode(RED_LED_PIN, OUTPUT);

    // Buzzer
    pinMode(BUZZER_PIN, OUTPUT);

    // Start in safe state
    setServoLocked();
    clearIndicators();
}

// ── Servo Control ───────────────────────────────────────────────────

void setServoLocked() {
    ledcWrite(SERVO_CHANNEL, SERVO_LOCKED);
}

void setServoOpen() {
    ledcWrite(SERVO_CHANNEL, SERVO_OPEN);
}

// ── Indicator Control ───────────────────────────────────────────────

void clearIndicators() {
    digitalWrite(GREEN_LED_PIN, LOW);
    digitalWrite(RED_LED_PIN, LOW);
    digitalWrite(BUZZER_PIN, LOW);
}

void setGrantIndicators() {
    digitalWrite(GREEN_LED_PIN, HIGH);
    digitalWrite(RED_LED_PIN, LOW);
    // Two short beeps
    digitalWrite(BUZZER_PIN, HIGH);
    delay(100);
    digitalWrite(BUZZER_PIN, LOW);
    delay(100);
    digitalWrite(BUZZER_PIN, HIGH);
    delay(100);
    digitalWrite(BUZZER_PIN, LOW);
}

void setDenyIndicators() {
    digitalWrite(GREEN_LED_PIN, LOW);
    digitalWrite(RED_LED_PIN, HIGH);
    digitalWrite(BUZZER_PIN, HIGH);
}

// ── RFID Polling ────────────────────────────────────────────────────

void pollRfid() {
    if (!g_rfid.PICC_IsNewCardPresent() || !g_rfid.PICC_ReadCardSerial()) {
        return;
    }

    // Build hex UID string
    String uid = "";
    for (byte i = 0; i < g_rfid.uid.size; i++) {
        if (g_rfid.uid.uidByte[i] < 0x10) uid += "0";
        uid += String(g_rfid.uid.uidByte[i], HEX);
    }
    uid.toUpperCase();

    // Generate unique event ID
    g_eventCounter++;
    String eventId = String("rfid-") + String(g_eventCounter);

    // Instant hardware feedback on card touch
    digitalWrite(GREEN_LED_PIN, HIGH);
    digitalWrite(BUZZER_PIN, HIGH);
    delay(40);
    digitalWrite(BUZZER_PIN, LOW);
    digitalWrite(GREEN_LED_PIN, LOW);

    sendRfidDetected(uid, eventId);

    g_rfid.PICC_HaltA();
    g_rfid.PCD_StopCrypto1();
}

// ── Serial Command Processing ───────────────────────────────────────

void processSerialInput() {
    while (Serial.available()) {
        String line = Serial.readStringUntil('\n');
        line.trim();
        if (line.length() == 0) continue;
        if (line.length() > MAX_JSON_FRAME_BYTES) {
            sendCommandResult("unknown", "error_frame_too_large");
            continue;
        }

        AccessCommand cmd = parseAccessCommand(line);
        if (!cmd.valid) {
            sendCommandResult("unknown", "error_parse_failed");
            // Stale/corrupt → go to CLOSED_SAFE
            if (g_state == DeviceState::IDLE) {
                g_state = DeviceState::CLOSED_SAFE;
            }
            continue;
        }

        handleAccessCommand(cmd);
    }
}

void handleAccessCommand(const AccessCommand& cmd) {
    // Duplicate command protection
    if (cmd.commandId == g_lastExecutedId) {
        sendCommandResult(cmd.commandId, "duplicate_ignored");
        return;
    }

    // Only accept commands when IDLE
    if (g_state != DeviceState::IDLE) {
        sendCommandResult(cmd.commandId, "rejected_busy");
        return;
    }

    g_lastExecutedId = cmd.commandId;

    if (cmd.decision == "grant") {
        g_currentHoldMs = cmd.doorHoldMs;
        setGrantIndicators();
        g_state = DeviceState::OPENING;
        g_actionStartMs = millis();
        sendCommandResult(cmd.commandId, "executed");
    }
    else if (cmd.decision == "deny") {
        setDenyIndicators();
        g_state = DeviceState::DENY_INDICATION;
        g_actionStartMs = millis();
        sendCommandResult(cmd.commandId, "executed");
    }
    else {
        sendCommandResult(cmd.commandId, "error_unknown_decision");
    }
}
