# Project Charter — DualKey

**Document ID:** `DOC-00-CHARTER`  
**Status:** Approved Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Executive Summary

DualKey is a prototype physical access control system designed to demonstrate robust, multi-factor physical identity verification by binding **something you have** (a 13.56 MHz RFID credential) with **something you are** (facial biometrics via OpenCV LBPH).

Traditional low-cost physical access control systems rely solely on RFID cards or PINs, making them susceptible to theft, borrowing, or credential sharing. DualKey bridges the gap between low-cost microcontroller hardware and local computer-vision processing to enforce strict two-factor authentication without requiring costly enterprise cloud infrastructure.

---

## 2. Project Vision & Mission

* **Vision:** Demonstrate an educational, transparent, and verifiable multi-factor physical access controller adhering to rigorous software engineering and systems design principles.
* **Mission:** Build a functional, fail-closed, single-door prototype combining an ESP32 microcontroller and a laptop computer that enforces two-factor identity correlation within a 10-second verification window.

---

## 3. Core Problem Statement

Unattended RFID access systems cannot distinguish between an authorized card owner and an unauthorized card possessor. When a card is stolen or shared, security is immediately breached. DualKey solves this problem at an educational prototype scale by requiring the cardholder to present their face to a camera immediately after tapping the card, confirming that the face matches the registered card owner.

---

## 4. Primary Stakeholders & Roles

| Role | Responsibility |
| :--- | :--- |
| **Lead Software Architect** | Establishes domain boundaries, design contracts, and ensures clean architecture. |
| **Systems & Embedded Engineer** | Designs ESP32 firmware, hardware pinout, serial protocol framing, and actuator timing. |
| **AI / Computer Vision Engineer** | Calibrates OpenCV Haar cascade face detector and LBPH face recognizer; defines biometric thresholds. |
| **Test Operator / QA Engineer** | Executes negative path testing, spoofing evaluation, and hardware-in-the-loop verification. |
| **Authorized End User** | Possesses an enrolled RFID card and presents enrolled face for access grant. |
| **Unauthorized User / Intruder**| Presents cloned card, wrong face, or presentation attack to evaluate fail-closed safety. |

---

## 5. High-Level Success Criteria

1. **Deterministic Identity Binding:** The system never unlocks for a valid RFID card when an unauthorized face or no face is presented.
2. **Strict Verification Window:** Face verification strictly terminates after 10.0 seconds measured with monotonic time, denying access upon expiration.
3. **Fail-Closed Safety:** In the event of serial disconnection, camera failure, malformed packets, or power interruption, the physical actuator remains locked.
4. **Architectural Cleanliness:** The application domain contains zero dependencies on OpenCV, serial drivers, or GPIO hardware, allowing complete unit testability in mock environments.
5. **Radical Transparency:** The system explicitly acknowledges and documents its biometric vulnerabilities, notably susceptibility to 2D photograph spoofing.
