// SPDX-License-Identifier: MIT
// DualKey ESP32 Firmware — NDJSON Protocol Serialization
//
// Reference: DOC-04-SERIAL (docs/04-interfaces/serial-message-contract.md)

#ifndef DUALKEY_PROTOCOL_H
#define DUALKEY_PROTOCOL_H

#include <ArduinoJson.h>
#include "config.h"

// ── Outgoing Messages (ESP32 → Host) ────────────────────────────────

inline void sendRfidDetected(const String& uid, const String& eventId) {
    JsonDocument doc;
    doc["v"]        = PROTOCOL_VERSION;
    doc["type"]     = "rfid_detected";
    doc["event_id"] = eventId;
    doc["uid"]      = uid;

    serializeJson(doc, Serial);
    Serial.println();
}

inline void sendCommandResult(const String& commandId, const String& status) {
    JsonDocument doc;
    doc["v"]          = PROTOCOL_VERSION;
    doc["type"]       = "command_result";
    doc["command_id"] = commandId;
    doc["status"]     = status;

    serializeJson(doc, Serial);
    Serial.println();
}

inline void sendHeartbeat(unsigned long uptimeMs) {
    JsonDocument doc;
    doc["v"]         = PROTOCOL_VERSION;
    doc["type"]      = "heartbeat";
    doc["event_id"]  = String("hb-") + String(uptimeMs);
    doc["uptime_ms"] = uptimeMs;

    serializeJson(doc, Serial);
    Serial.println();
}

// ── Incoming Message Parsing (Host → ESP32) ─────────────────────────

struct AccessCommand {
    String commandId;
    String sessionId;
    String decision;
    String reason;
    int    doorHoldMs;
    bool   valid;
};

inline AccessCommand parseAccessCommand(const String& line) {
    AccessCommand cmd;
    cmd.valid = false;

    JsonDocument doc;
    DeserializationError err = deserializeJson(doc, line);

    if (err) return cmd;
    if (doc["v"].as<int>() != PROTOCOL_VERSION) return cmd;

    const char* type = doc["type"];
    if (type == nullptr || strcmp(type, "access_command") != 0) return cmd;

    cmd.commandId  = doc["command_id"].as<String>();
    cmd.sessionId  = doc["session_id"].as<String>();
    cmd.decision   = doc["decision"].as<String>();
    cmd.reason     = doc["reason"].as<String>();
    cmd.doorHoldMs = doc["door_hold_ms"] | DOOR_HOLD_MS;
    cmd.valid      = true;

    return cmd;
}

#endif // DUALKEY_PROTOCOL_H
