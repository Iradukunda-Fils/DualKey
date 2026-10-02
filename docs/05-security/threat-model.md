# STRIDE Threat Model & Security Posture

**Document ID:** `DOC-05-THREAT`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Threat Analysis Methodology (STRIDE)

DualKey's threat landscape is evaluated using Microsoft's STRIDE model to identify attack vectors against its physical access boundary.

```text
[Attacker Vector]
       │
       ├── S: Spoofing (Printed photograph, Cloned RFID UID)
       ├── T: Tampering (Serial line injection, Database editing)
       ├── R: Repudiation (Disputing entry event, Missing audit log)
       ├── I: Information Disclosure (Cleartext serial logs, Face samples)
       ├── D: Denial of Service (Camera occlusion, Serial bus flooding)
       └── E: Elevation of Privilege (Unilateral unlock commands)
```

---

## 2. STRIDE Assessment Matrix

| STRIDE Category | Threat Description | Severity | Countermeasure / Mitigation in Prototype | Residual Risk & Prototype Acceptance Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **Spoofing (Biometric)** | Attacker holds a printed 2D photograph or mobile screen of an authorized user in front of the camera. | **High** | None in software baseline. Mitigated operationally by physical observation and camera field-of-view positioning. | **Accepted Prototype Limitation.** LBPH has no liveness detection. Fully disclosed in `DOC-05-LIMIT`. |
| **Spoofing (RFID)** | Attacker uses a Proxmark3 or Flipper Zero to clone and replay a card UID. | **Medium** | Mandatory biometric second factor. Replaying a valid card UID will fail unless the authorized face is also presented. | **Accepted.** Prototype treats UID as an unauthenticated identifier, not a cryptographic secret. |
| **Tampering (Serial)** | Attacker connects to the USB serial bus and injects an `access_command(grant)` message. | **Medium** | Host-generated UUIDv4 `command_id` and `session_id` required. ESP32 accepts commands only matching active session IDs. | **Accepted.** Physical enclosure protects the internal USB link. Serial bus is locally trusted. |
| **Tampering (Database)**| Attacker directly edits `app.db` to insert an unauthorized card or bind an unauthorized face label. | **High** | Linux host user permissions (`chmod 600 data/app.db`). Process runs under dedicated unprivileged account. | **Accepted.** Standard local OS security controls protect filesystem assets. |
| **Repudiation** | An authorized user denies entering a secure area. | **Low** | Immutable audit event log (`access_events` table) storing exact timestamps, card UIDs, and decision reasons. | **Mitigated.** Audit logs are append-only. |
| **Information Disclosure** | Extraction of enrolled facial images or cardholder full names from disk. | **Low** | Stored locally in `data/faces/`. No cloud uploads or external network transmission. | **Mitigated.** Fully offline local data sovereignty. |
| **Denial of Service** | Physical occlusion of the camera lens or flooding the RFID reader with continuous taps. | **Medium** | Hardware debounce on RFID ($500\text{ ms}$). Host strictly enforces 10.0s session timeout. Fails closed. | **Mitigated.** Fails closed. Attackers cannot force door opening through DoS. |
| **Elevation of Privilege**| Microcontroller attempts to unilaterally grant access without host authorization. | **Critical**| ESP32 firmware contains zero biometric code and zero lookup tables. Firmware can only actuate upon receiving host commands. | **Mitigated.** Single authoritative decision point at the host policy layer. |
