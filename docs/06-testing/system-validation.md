# System Validation Report

> DOC-06-SYSVAL | Phase 12 Validation

## 1. Multi-Frame Validation

The authorization policy requires `required_consistent_matches` consecutive
frames where the recognized identity matches the card owner before granting
access. Default: 3 frames.

### 1.1 Automated Test Results

| Pattern | Sequence | Expected | Test Result |
|---------|----------|----------|-------------|
| A A A | 3 owner matches | GRANT | See `test_multiframe_validation.py` |
| A A B | 2 owner + 1 wrong | DENY (mismatch) | See `test_multiframe_validation.py` |
| A B A | owner, wrong, owner | DENY on B frame | See `test_multiframe_validation.py` |
| A UNKNOWN A | owner, unrecognized, owner | No immediate grant | See `test_multiframe_validation.py` |
| A A UNKNOWN | 2 owner + 1 unrecognized | No grant on frame 3 | See `test_multiframe_validation.py` |

### 1.2 Enforcement Mechanism

The `AuthorizationPolicy.evaluate()` function in `app/domain/decisions.py`:
1. Checks session deadline (timeout -> DENY)
2. Validates biometric frame (no face, multi-face -> CONTINUE/DENY)
3. Checks recognition threshold
4. Verifies recognized_person == expected_person (mismatch -> DENY)
5. Increments `session.match_count` only on valid owner match
6. Returns GRANT only when `match_count >= required_matches`

Any mismatch resets the consecutive counter or immediately denies.

## 2. Authorization Matrix Validation

### 2.1 Combination Results

| RFID | Face | Expected | Reason | Test |
|------|------|----------|--------|------|
| Correct | Owner's face | GRANT | MATCHED_OWNER | `test_correct_rfid_correct_face_grants` |
| Correct | Wrong person | DENY | FACE_MISMATCH | `test_correct_rfid_wrong_face_denies` |
| Correct | Unknown face | DENY | TIMEOUT | `test_correct_rfid_unknown_face_denies` |
| Unknown | Owner's face | DENY | UNKNOWN_RFID | `test_unknown_rfid_correct_face_denies` |
| Unknown | Wrong person | DENY | UNKNOWN_RFID | `test_unknown_rfid_wrong_face_denies` |
| Correct | No face | DENY | TIMEOUT | `test_correct_rfid_no_face_timeout` |
| Correct | Multiple faces | DENY | MULTIPLE_FACES | `test_correct_rfid_multiple_faces_denies` |
| Correct | Face after 10s | DENY | TIMEOUT | `test_correct_rfid_face_after_timeout_denies` |

### 2.2 Invariant

> Only the correct owner within the active verification window can reach ACCESS_GRANTED.
> Everything else results in ACCESS_DENIED (fail-closed).

This invariant is enforced by:
- `IdentityRepository.get_card_owner()` for RFID validation
- `AuthorizationPolicy.evaluate()` for biometric + temporal validation
- `AccessController._deny_and_reset()` for all denial paths

## 3. Failure Injection Validation

### 3.1 Automated Test Results

| Failure Mode | Expected Behavior | Door State | Test |
|-------------|-------------------|------------|------|
| Camera disconnected (None frames) | Timeout after window | CLOSED | `test_camera_returns_none_no_grant` |
| Transport disconnected | Health check fails -> FAULT | CLOSED | `test_transport_disconnected_faults` |
| Heartbeat stale (>3s) | Health check fails -> FAULT | CLOSED | `test_heartbeat_stale_faults` |
| Malformed RFID event | Event ignored | CLOSED | `test_malformed_rfid_event_ignored` |
| Single no-face frame | Session continues | CLOSED (until grant) | `test_session_survives_single_no_face` |
| Session timeout | DENY command sent | CLOSED | `test_timeout_closes_door` |
| Idle state | No commands sent | CLOSED | `test_idle_state_is_safe` |

### 3.2 Fail-Closed Invariant

For every failure mode tested:
- **The door remains closed** unless a valid authorization decision has already been safely completed.
- Denial commands are sent to the ESP32 to activate red LED + buzzer.
- The system transitions back to IDLE after handling the failure.

## 4. Hardware-in-Loop Validation

### 4.1 Procedure

> [!IMPORTANT]
> Hardware validation requires the physical test setup:
> ESP32 + MFRC522 + Servo + LEDs + Buzzer + Laptop webcam

1. Flash firmware: `cd firmware && pio run -t upload`
2. Start access loop: `.venv/bin/python -m app.main --run --model lbph`
3. Tap enrolled RFID card, present enrolled face -> verify servo opens
4. Tap enrolled RFID card, present wrong face -> verify red LED + buzzer
5. Tap unknown RFID card -> verify immediate denial
6. Tap enrolled card, wait 10s -> verify timeout denial
7. Disconnect USB serial during session -> verify system transitions to FAULT
8. Reconnect and verify system recovers to IDLE

### 4.2 Results

| Test | RFID | Face | Servo | Green LED | Red LED | Buzzer | Result |
|------|------|------|-------|-----------|---------|--------|--------|
| Grant | Enrolled | Owner | Opens 90deg | ON | OFF | 2 beeps | PENDING |
| Wrong face | Enrolled | Other | Stays 0deg | OFF | ON | Continuous | PENDING |
| Unknown card | Unknown | N/A | Stays 0deg | OFF | ON | Continuous | PENDING |
| Timeout | Enrolled | None | Stays 0deg | OFF | ON | Continuous | PENDING |
| Disconnect | N/A | N/A | Stays 0deg | N/A | N/A | N/A | PENDING |

## 5. Security Limitation: Printed Photograph

### 5.1 Test Procedure

1. Enroll a person normally with live face
2. Print a clear photograph of the enrolled person's face
3. Present the photograph to the webcam during verification
4. Record whether recognition succeeds or fails

### 5.2 Expected Behavior

Neither LBPH nor SFace includes liveness detection. Both models may accept
a sufficiently clear printed photograph under favorable conditions.

**This is a known, documented biometric limitation** (DOC-05-BIO).

### 5.3 Observations

| Model | Distance | Lighting | Threshold | Photo Accepted? | Score |
|-------|----------|----------|-----------|----------------|-------|
| LBPH | PENDING | PENDING | 65.0 | PENDING | PENDING |
| SFace | PENDING | PENDING | 0.363 | PENDING | PENDING |

> [!CAUTION]
> This system does NOT include liveness detection. A printed photograph
> may be accepted under favorable conditions. This is explicitly documented
> as an MVP limitation, not a defect. Production systems must add
> anti-spoofing measures.
