# System Configuration & Parameter Reference

**Document ID:** `DOC-07-CONFIG`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Configuration Keys & Defaults

All runtime parameters are consolidated in `SystemConfig` and can be overridden via environment variables or a local `.env` file.

| Configuration Key | Environment Variable | Default Value | Unit | Engineering Description |
| :--- | :--- | :--- | :--- | :--- |
| `verification_window_s` | `DUALKEY_WINDOW_SEC` | `10.0` | Seconds | Duration of active biometric verification window following RFID tap. |
| `door_hold_s` | `DUALKEY_HOLD_SEC` | `3.0` | Seconds | Time servo latch remains unlocked upon access grant. |
| `required_consistent_matches`| `DUALKEY_MATCH_COUNT` | `3` | Frames | Number of consecutive positive matching frames required to grant access. |
| `lbph_threshold` | `DUALKEY_LBPH_THRESHOLD`| `65.0` | Distance | Chi-square distance ceiling. Values above this are rejected as low confidence. |
| `camera_index` | `DUALKEY_CAMERA_INDEX` | `0` | Index | V4L2 video device index (`0` maps to `/dev/video0`). |
| `serial_port` | `DUALKEY_SERIAL_PORT` | `"/dev/ttyUSB0"` | Device | USB CDC device path for ESP32 serial communication. |
| `serial_baud` | `DUALKEY_SERIAL_BAUD` | `115200` | Baud | UART transmission speed. Must match firmware `config.h`. |
| `heartbeat_interval_s` | `DUALKEY_HB_INTERVAL` | `1.0` | Seconds | Expected periodicity of device heartbeat telemetry. |
| `heartbeat_timeout_s` | `DUALKEY_HB_TIMEOUT` | `3.0` | Seconds | Missed heartbeat threshold before transitioning to `FAULT`. |
| `allow_multiple_faces` | `DUALKEY_ALLOW_MULTI` | `false` | Boolean | Safety flag. If false, frames with $>1$ face cause immediate denial. |

---

## 2. Configuration Validation Rules

Upon host initialization:
1. `verification_window_s` must be in range $[3.0, 30.0]$.
2. `door_hold_s` must be in range $[1.0, 10.0]$.
3. `required_consistent_matches` must be $\ge 1$ (recommended $\ge 3$).
4. `lbph_threshold` must be positive float ($> 0.0$).
5. `serial_port` must exist on the filesystem or an exception is logged.
