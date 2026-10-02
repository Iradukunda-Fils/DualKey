# Acceptance Testing Procedures

**Document ID:** `DOC-06-ACCEPT`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Acceptance Protocol Overview

The acceptance test battery translates the 10 operational criteria (`ACC-001` through `ACC-010`) into standardized operator execution procedures.

---

## 2. Test Execution Procedures

### Procedure for `ACC-001` (Authorized Access)
1. Ensure DualKey host is in `IDLE` state.
2. Present enrolled Card A to MFRC522 antenna.
3. Look directly into laptop camera.
4. **Pass Criteria:** Green LED turns on, buzzer chirps twice, servo rotates to $90^\circ$ within $1.5\text{ s}$, holds open for $3\text{ s}$, then returns to $0^\circ$.

### Procedure for `ACC-002` (Biometric Mismatch)
1. Present enrolled Card A (owned by Alice).
2. Person B (enrolled test user Bob) looks into the camera.
3. **Pass Criteria:** Servo remains firmly at $0^\circ$. Red LED turns on, buzzer sounds a $1.5\text{ s}$ long buzz. Log indicates `FACE_MISMATCH`.

### Procedure for `ACC-003` (Unknown RFID)
1. Present un-enrolled RFID Card X.
2. **Pass Criteria:** Servo remains locked. Red LED turns on with a long buzz. Camera is never triggered.

### Procedure for `ACC-004` (No Face / Timeout)
1. Present enrolled Card A.
2. Step out of camera view for 10 seconds.
3. **Pass Criteria:** At exactly $10.0\text{ s}$, Red LED turns on and buzzer sounds a long buzz. Door never opens.

### Procedure for `ACC-005` (Presentation Too Late)
1. Present enrolled Card A.
2. Wait 11 seconds away from camera, then step in front of the lens.
3. **Pass Criteria:** System denies access at $10.0\text{ s}$; stepping in front at $11\text{ s}$ causes no reaction.

### Procedure for `ACC-007` (Multiple Faces)
1. Present enrolled Card A.
2. Two people position their faces in front of the camera simultaneously.
3. **Pass Criteria:** Red LED turns on, long buzz sounds. Door remains locked. Log records `MULTIPLE_FACES`.

### Procedure for `ACC-010` (Printed Photo Presentation Test)
1. Present enrolled Card A.
2. Hold a high-resolution printed color photograph of Person A in front of the camera.
3. **Observation:** System may grant access (as documented in `DOC-05-LIMIT`).
4. **Pass Criteria:** The limitation is verified to match system documentation; event log records distance metric for audit analysis.
