# ADR-0002: Laptop Host Owns Computer Vision & Face Recognition

**Document ID:** `ADR-0002`  
**Status:** Accepted  
**Date:** September 29, 2026  
**Deciders:** Lead Software Architect, Systems Engineer, Embedded Engineer  

---

## 1. Context & Problem Statement

DualKey requires real-time face detection and LBPH biometric inference. The system architecture must determine whether computer vision processing should execute on the ESP32 microcontroller (e.g. via an ESP32-CAM module) or on the local laptop host utilizing its integrated webcam.

---

## 2. Decision

Face detection, image preprocessing, LBPH model training, and recognition inference are **owned exclusively by the laptop host**. The ESP32 is strictly prohibited from executing computer vision algorithms.

---

## 3. Rationale

1. **Computational Capacity:** The standard ESP32 (Xtensa LX6 @ 240 MHz with 520 KB SRAM) lacks the memory and floating-point throughput to run OpenCV's C++ library, maintain image frame buffers ($640 \times 480 \times 3 \approx 900\text{ KB}$ raw), and execute real-time Haar cascades.
2. **Development Velocity:** Python with `opencv-contrib-python` on Linux provides superior debugging, visualization, sample storage, and model retraining capabilities.
3. **Hardware Simplicity:** Leveraging the laptop's built-in webcam eliminates the need for specialized ESP32-CAM modules, ribbon cables, and external PSRAM chips on the breadboard.

---

## 4. Consequences

### Positive
* High frame rate ($\ge 15\text{ FPS}$) achievable on laptop CPU.
* Fast enrollment, dynamic retraining, and local disk model storage.
* Keeps ESP32 firmware lightweight, deterministic, and highly responsive to SPI RFID interrupts.

### Negative / Trade-offs
* Requires a running laptop host process to operate the door.
