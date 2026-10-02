# Software Requirements Specification

**Document ID:** `DOC-01-SW`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Overview

This document specifies the software environments, runtimes, core dependencies, and platform requirements for both the laptop host application and the ESP32 embedded firmware.

---

## 2. Requirement Specifications

### SW-001: Host Runtime Environment
* **Platform:** Linux POSIX environment (Ubuntu 22.04 LTS or Debian 12 compatible).
* **Python Runtime:** Python 3.10, 3.11, or 3.12 64-bit runtime.
* **Packaging:** Managed via Python virtual environment (`venv`) with dependencies declared in `requirements.txt` or `pyproject.toml`.

### SW-002: Computer Vision Stack
* **Library:** `opencv-contrib-python` version $\ge 4.8.0$ (MANDATORY: must include the `opencv_contrib` face module).
* **Core APIs:**
  * Face Detection: `cv2.CascadeClassifier` loaded with `haarcascade_frontalface_default.xml`.
  * Preprocessing: `cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)`, `cv2.resize()`, `cv2.equalizeHist()`.
  * Face Recognition: `cv2.face.LBPHFaceRecognizer_create(radius=1, neighbors=8, grid_x=8, grid_y=8)`.
  * Model Storage: `recognizer.write("data/models/lbph.yml")` and `recognizer.read("data/models/lbph.yml")`.

### SW-003: Embedded Firmware Toolchain
* **Build System:** PlatformIO Core (CLI) or Arduino IDE with ESP32 board support package $\ge 2.0.11$.
* **Language Standard:** C++17.
* **Firmware Libraries:**
  * `bblanchon/ArduinoJson` version 6.21+ or 7.x (for robust NDJSON serialization and deserialization).
  * `miguelbalboa/rfid` (MFRC522 library for SPI communication).
  * ESP32 native `ESP32Servo` or native `ledc` HAL for PWM timing.

### SW-004: Relational Persistence Engine
* **Engine:** SQLite 3 embedded relational database driver (`sqlite3` standard Python library).
* **Mode:** Write-Ahead Logging (`PRAGMA journal_mode=WAL;`) and foreign keys enabled (`PRAGMA foreign_keys=ON;`).
* **Database File:** Stored locally at `data/app.db`.

### SW-005: Serial Communication Driver
* **Library:** `pyserial` version $\ge 3.5$.
* **Configuration:** 115200 baud, 8N1, read timeout $0.1\text{ s}$, non-blocking buffer polling.

### SW-006: Test & Verification Framework
* **Host Testing:** `pytest` $\ge 7.4.0$ with `pytest-cov` and `unittest.mock`.
* **Coverage Target:** Minimum $90\%$ statement coverage across `app/domain/` and `app/application/`.
* **Linting & Typing:** `ruff` or `flake8` for linting; `mypy` for static type checking with strict type annotations on all ports and domain models.
