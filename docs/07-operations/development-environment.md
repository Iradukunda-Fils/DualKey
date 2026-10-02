# Development Environment Setup

**Document ID:** `DOC-07-ENV`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Prerequisites (Linux Host)

DualKey is developed and validated on modern Linux environments (Ubuntu 22.04 LTS / Debian 12 / Fedora 38+).

### System Packages Installation
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip libgl1-mesa-glx libglib2.0-0 v4l-utils
```

---

## 2. Python Virtual Environment Setup

```bash
# 1. Create a clean virtual environment
python3 -m venv .venv

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Upgrade pip and install wheel
pip install --upgrade pip setuptools wheel

# 4. Install dependencies
pip install opencv-contrib-python>=4.8.0 pyserial>=3.5 pytest>=7.4 pytest-cov mypy ruff pyyaml
```

---

## 3. Hardware Device Permissions (udev Rules)

To access `/dev/ttyUSB0` and `/dev/video0` without requiring `sudo`:

```bash
# Add current user to dialout and video groups
sudo usermod -a -G dialout,video $USER

# Create udev rule for standard USB serial adapters
sudo tee /etc/udev/rules.d/99-dualkey-esp32.rules << 'EOF'
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", MODE="0666", GROUP="dialout"
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", MODE="0666", GROUP="dialout"
EOF

sudo udevadm control --reload-rules
sudo udevadm trigger
```
*(Log out and back in for group changes to take effect).*

---

## 4. ESP32 Firmware Build Environment (PlatformIO)

```bash
# Install PlatformIO Core CLI
pip install platformio

# Compile firmware
cd firmware
pio run

# Flash to connected ESP32
pio run --target upload --upload-port /dev/ttyUSB0

# Open serial monitor
pio device monitor --port /dev/ttyUSB0 --baud 115200
```
