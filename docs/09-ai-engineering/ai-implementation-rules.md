# AI Implementation Rules & Code Standards

**Document ID:** `DOC-09-RULES`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Domain Cleanliness Rules

1. **Zero External Frameworks in Domain:**
   * Files in `app/domain/` (`models.py`, `states.py`, `decisions.py`, `reason_codes.py`) must contain **ZERO** imports of `cv2`, `numpy`, `serial`, `sqlite3`, `torch`, or any I/O library.
   * Domain classes must be pure Python standard library only (`dataclasses`, `enum`, `typing`).

2. **No Boolean Flag State Machines:**
   * Never introduce loose boolean flags like `is_card_ready = True`, `is_face_verified = True`, or `door_unlocked = False`.
   * State must be explicitly tracked using the canonical `SessionState` enum.

3. **No Direct Hardware Cross-Talk:**
   * The host application must never attempt direct GPIO or PWM manipulation. All actuation commands must pass through `DeviceTransportPort` as NDJSON messages.
   * Firmware must never parse images or attempt biometric decisions.

4. **Monotonic Timing Enforcement:**
   * Never use `time.time()` for session timeouts or deadline evaluations. Always use `time.monotonic()` (or `ClockPort.now_monotonic()`).

5. **Strict Typing & Linting:**
   * All Python functions must declare argument and return type annotations.
   * Code must pass `mypy --strict` and `ruff check` with zero errors.
