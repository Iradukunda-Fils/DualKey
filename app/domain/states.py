# SPDX-License-Identifier: MIT
"""Session state machine enumeration.

Defines the canonical FSM states for DualKey access-control sessions.
State transitions are governed by AccessController; this module only
declares the valid state vocabulary.

Reference: DOC-02-STATE (docs/02-architecture/state-machine.md)
"""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class SessionState(StrEnum):
    """Canonical host FSM states for a DualKey access session.

    Each state has a single entry condition, a set of allowed host actions,
    and well-defined exit transitions documented in DOC-02-STATE.
    """

    IDLE = "IDLE"
    """System is idle, listening for incoming RFID events."""

    CARD_VALIDATING = "CARD_VALIDATING"
    """An rfid_detected event was received; querying IdentityRepository."""

    VERIFYING = "VERIFYING"
    """Card is valid and registered. Biometric verification is in progress
    within the 10.0s monotonic deadline window."""

    GRANTED = "GRANTED"
    """Authorization formula evaluated to TRUE with N >= 3 stable matches.
    Door is commanded to open position."""

    DENIED = "DENIED"
    """Access denied due to unknown card, face mismatch, or multiple faces.
    Red LED and buzzer active for 1500ms."""

    TIMEOUT = "TIMEOUT"
    """Monotonic clock exceeded session deadline during VERIFYING.
    Treated as denial — servo locked, red LED and buzzer active."""

    FAULT = "FAULT"
    """System fault — camera disconnect, serial link drop, or storage error.
    All access requests rejected. Actuator remains locked."""
