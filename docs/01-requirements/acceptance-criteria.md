# Operational Acceptance Criteria

**Document ID:** `DOC-01-ACC`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Overview & Verification Gate

The following 10 acceptance criteria (`ACC-001` through `ACC-010`) define the binary operational pass/fail conditions required to authorize the DualKey prototype for delivery.

Each criterion specifies preconditions, input sequences, observable hardware outputs, and audit expectations.

---

## 2. Acceptance Scenarios

| Test ID | Scenario Description | Inputs / Injected Stimuli | Expected Hardware Behavior | Expected Audit / Log Event | Pass / Fail Gate |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`ACC-001`** | **Authorized Access (Happy Path)** | Enrolled Card A presented; enrolled Person A face presented within $10.0\text{ s}$. | Green LED illuminates; two short beeps emit; servo rotates to open ($90^\circ$); holds for $3\text{ s}$; returns to locked ($0^\circ$). | `AccessEvent(decision='GRANT', reason='MATCHED_OWNER', expected='PersonA', observed='PersonA')` | **PASS:** Door opens and relocks safely. |
| **`ACC-002`** | **Biometric Mismatch (Wrong Face)** | Enrolled Card A presented; enrolled Person B face presented. | Servo remains firmly locked ($0^\circ$); Red LED illuminates; single long buzz ($1.5\text{ s}$). | `AccessEvent(decision='DENY', reason='FACE_MISMATCH', expected='PersonA', observed='PersonB')` | **PASS:** Door strictly closed; instant rejection. |
| **`ACC-003`** | **Unregistered Credential** | Unenrolled RFID Card X presented. | Servo remains locked ($0^\circ$); Red LED illuminates; long buzz. Camera is NOT activated. | `AccessEvent(decision='DENY', reason='UNKNOWN_RFID', card_uid='CARD_X')` | **PASS:** Door strictly closed; session never opens. |
| **`ACC-004`** | **No Face Presented** | Enrolled Card A presented; empty camera view for $10.0\text{ s}$. | Servo remains locked ($0^\circ$); at $T = 10.0\text{ s}$, Red LED illuminates; long buzz. | `AccessEvent(decision='DENY', reason='TIMEOUT', expected='PersonA')` | **PASS:** Door strictly closed; timeout after 10s. |
| **`ACC-005`** | **Biometric Presentation Too Late** | Enrolled Card A presented; Person A steps in front of camera at $T = 10.2\text{ s}$. | Servo remains locked ($0^\circ$); session has already terminated at $10.0\text{ s}$; Red LED illuminates. | `AccessEvent(decision='DENY', reason='TIMEOUT')` logged at $10.0\text{ s}$. Late frames ignored. | **PASS:** Late arrival strictly denied. |
| **`ACC-006`** | **Card / Identity Swap** | Enrolled Card B presented; enrolled Person A face presented. | Servo remains locked ($0^\circ$); Red LED illuminates; long buzz. | `AccessEvent(decision='DENY', reason='FACE_MISMATCH', expected='PersonB', observed='PersonA')` | **PASS:** Door strictly closed. |
| **`ACC-007`** | **Multiple Faces in Frame** | Enrolled Card A presented; two people look into the webcam simultaneously. | Servo remains locked ($0^\circ$); Red LED illuminates; long buzz. | `AccessEvent(decision='DENY', reason='MULTIPLE_FACES', expected='PersonA')` | **PASS:** Ambiguous biometric scene denied. |
| **`ACC-008`** | **Camera Hardware Failure** | Enrolled Card A presented; webcam unplugged or `/dev/video0` inaccessible. | Servo remains locked ($0^\circ$); Red LED illuminates; system enters `FAULT` state. | `AccessEvent(decision='DENY', reason='CAMERA_ERROR')` logged. | **PASS:** Immediate fail-closed transition. |
| **`ACC-009`** | **Serial Link Interruption** | Card A presented; USB serial cable disconnected during verification window. | Servo remains locked ($0^\circ$); ESP32 returns to autonomous safe state; host logs fault. | `AccessEvent(decision='DENY', reason='DEVICE_LINK_ERROR')` logged on host. | **PASS:** Fail-closed; no orphaned unlocks. |
| **`ACC-010`** | **Printed Photograph Spoofing Test** | Enrolled Card A presented; high-res printed color photo of Person A presented. | Servo may open (Grant); Green LED may illuminate. | Verification that event is logged and limitation is fully documented in `docs/05-security/`. | **PASS:** Known limitation verified & acknowledged. |
