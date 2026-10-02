# Biometric Limitations & Presentation-Attack Disclosure

**Document ID:** `DOC-05-LIMIT`  
**Status:** Approved Security Disclosure  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Explicit Biometric Vulnerability Disclosure

> [!CAUTION]
> **CRITICAL SECURITY DISCLOSURE:**
> **A printed 2D photograph or mobile device screen displaying an enrolled user's face may fool the OpenCV LBPH recognizer.**
> 
> DualKey is strictly an educational systems-engineering prototype designed to demonstrate multi-factor architectural binding. It **does not** provide production-grade physical security.

---

## 2. What This MVP Does NOT Provide

To avoid false assumptions by operators, engineers, or evaluators, the following capabilities are explicitly declared as **NOT IMPLEMENTED**:

1. **No Liveness Detection:** The system cannot determine if a presented face is alive, breathing, or blinking.
2. **No Presentation-Attack Detection (PAD):** No spectral texture analysis, reflection detection, or motion parallax algorithms are deployed.
3. **No 3D Depth Sensing:** Standard UVC webcams capture monocular 2D RGB imagery; no structured light, Time-of-Flight (ToF), or stereoscopic sensors are used.
4. **No Infrared (IR) Verification:** Standard webcams cannot evaluate near-infrared reflectance or thermal heat signatures characteristic of living tissue.
5. **No Anti-Spoofing Guarantees:** Any attack presenting an optical facsimile of an enrolled face within the camera's focal plane with appropriate size and lighting may achieve a false acceptance.

---

## 3. LBPH Structural Limitations

The Local Binary Patterns Histograms (LBPH) algorithm operates by extracting micro-texture patterns from a grayscale image grid:
* It analyzes local pixel intensity gradients: $s(g_p - g_c)$.
* Because a high-resolution printed photograph or modern smartphone OLED display accurately reproduces the spatial intensity gradients of human skin and facial features, the calculated chi-square histogram distance can fall well below the acceptance threshold $\theta$.
* LBPH is computationally lightweight and runs deterministically on standard CPUs, making it ideal for educational architecture demonstrations, but it is fundamentally incapable of distinguishing 2D surfaces from 3D anatomical structures.

---

## 4. Prototype Classification & Usage Boundaries

| Attribute | DualKey Educational Prototype | Commercial High-Assurance Access Control |
| :--- | :--- | :--- |
| **Intended Purpose** | Systems-engineering educational demonstration of 2FA. | Perimeter defense for life safety, property, or high-value assets. |
| **Credential Technology** | Unauthenticated 13.56 MHz RFID UID (MFRC522). | Cryptographic Smart Card (MIFARE DESFire EV3, SEOS) with AES-128/256 SAM. |
| **Biometric Engine** | OpenCV 4.x LBPH (Grayscale 2D Histograms). | Deep Convolutional Neural Networks / Vision Transformers with embedded PAD. |
| **Liveness Sensor** | Standard monocular laptop webcam. | Multi-spectral 3D ToF, Structured Light, or Near-Infrared (NIR) sensor array. |
| **Compliance** | ISO/IEC 14443 Type A unauthenticated read. | ISO/IEC 30107-3 Presentation Attack Detection (iBeta Level 1 & 2 certified). |

DualKey must **never** be deployed or advertised as a bank-grade or high-assurance physical security product.
