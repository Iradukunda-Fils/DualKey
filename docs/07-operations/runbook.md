# Operator Runbook & Standard Operating Procedures

**Document ID:** `DOC-07-RUNBOOK`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Daily Operations & System Launch

### Starting the DualKey Controller
```bash
# 1. Activate Python virtual environment
cd /home/iradukunda/Lost/Learn/Auca-Innovation/IoT/DualKey
source .venv/bin/activate

# 2. Launch host application
python -m app.main
```
The console will output system initialization status, database connectivity, and confirm that the ESP32 serial link is active.

### Stopping the System
Send `SIGINT` (`Ctrl+C`). The application gracefully flushes audit logs, releases `/dev/video0`, closes the serial port, and shuts down cleanly.

---

## 2. User Enrollment Procedure

To onboard an authorized individual:
```bash
python -m app.main --enroll
```
1. Enter the user's full name when prompted (e.g. "Alice Johnson").
2. Have the user tap their physical RFID card against the MFRC522 sensor.
3. Position the user in front of the webcam. The CLI will automatically capture 20 normalized facial crops while guiding the user to turn their head slightly.
4. The system updates SQLite and retrains `data/models/lbph.yml`.
5. Have the user execute a test tap to confirm live verification before leaving the terminal.

---

## 3. Credential Revocation

To revoke a lost or compromised card:
```bash
python -m app.main --revoke-card <CARD_UID_HEX>
```
The card's status in `rfid_cards` is set to `REVOKED`. Subsequent taps of this card are rejected immediately with `UNKNOWN_RFID`.

---

## 4. Log Inspection & Audit Extraction

To review recent access attempts:
```bash
# View last 20 access decisions directly from SQLite
sqlite3 -header -column data/app.db \
  "SELECT timestamp, card_uid, expected_person_id, decision, reason FROM access_events ORDER BY timestamp DESC LIMIT 20;"
```
