# SPDX-License-Identifier: MIT
"""Machine-readable reason codes for every authorization outcome.

Every authorization decision, transient state, rejection, or system fault
is classified by exactly one ReasonCode from this catalog. Free-form error
messages are prohibited in core audit workflows.

Reference: DOC-04-CODES (docs/04-interfaces/error-codes.md)
"""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class ReasonCode(StrEnum):
    """Universal reason code taxonomy for DualKey access decisions.

    Categories:
        Success:   MATCHED_OWNER
        Transient: MATCH_IN_PROGRESS, FACE_NOT_FOUND, LOW_CONFIDENCE
        Rejection: UNKNOWN_RFID, FACE_MISMATCH, MULTIPLE_FACES, TIMEOUT
        Fault:     CAMERA_ERROR, DEVICE_LINK_ERROR, COMMAND_REJECTED,
                   ACTUATOR_FAILURE
    """

    # --- Success ---
    MATCHED_OWNER = "MATCHED_OWNER"
    """Full 2-factor binding validated with N >= 3 stable matches."""

    # --- Transient (session continues) ---
    MATCH_IN_PROGRESS = "MATCH_IN_PROGRESS"
    """Single positive frame recorded; awaiting stable match count."""

    FACE_NOT_FOUND = "FACE_NOT_FOUND"
    """No human face detected in current frame; scan continues."""

    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    """Detected face distance exceeds calibrated threshold."""

    # --- Rejection (immediate denial) ---
    UNKNOWN_RFID = "UNKNOWN_RFID"
    """Presented RFID card UID is not enrolled or is inactive."""

    FACE_MISMATCH = "FACE_MISMATCH"
    """Recognized face matches an enrolled person who is NOT the card owner."""

    MULTIPLE_FACES = "MULTIPLE_FACES"
    """Frame contains >1 face; scene rejected for ambiguity."""

    TIMEOUT = "TIMEOUT"
    """10.0-second monotonic verification window elapsed without match."""

    # --- System Faults ---
    CAMERA_ERROR = "CAMERA_ERROR"
    """Video capture device disconnected or frame read returned None."""

    DEVICE_LINK_ERROR = "DEVICE_LINK_ERROR"
    """USB serial connection lost or heartbeat missed for >3.0s."""

    COMMAND_REJECTED = "COMMAND_REJECTED"
    """Microcontroller reported parse error or invalid command parameters."""

    ACTUATOR_FAILURE = "ACTUATOR_FAILURE"
    """Command acknowledgement timed out without execution confirmation."""
