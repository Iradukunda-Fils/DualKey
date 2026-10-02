# SPDX-License-Identifier: MIT
"""Domain data models — pure, immutable entities with zero infrastructure imports.

All types in this module are plain Python dataclasses representing the core
identity and session concepts of DualKey. They carry no business logic beyond
trivial temporal predicates and are fully serialization-agnostic.

Reference: DOC-03-MODEL (docs/03-design/identity-model.md)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum


class UserStatus(StrEnum):
    """Enrollment lifecycle status for persons and RFID cards.

    A revoked entity is permanently excluded from authorization decisions.
    """

    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"


# ---------------------------------------------------------------------------
# Identity Entities
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Person:
    """An enrolled human identity in the DualKey system.

    Attributes:
        person_id: UUIDv4 unique identifier.
        display_name: Human-readable full name for audit logs.
        face_label: Integer label assigned by OpenCV LBPH recognizer (unique).
        status: Current enrollment status.
        created_at: UTC Unix epoch timestamp of enrollment.
    """

    person_id: str
    display_name: str
    face_label: int
    status: UserStatus = UserStatus.ACTIVE
    created_at: float = field(default_factory=time.time)


@dataclass(frozen=True)
class RFIDCard:
    """A bound RFID token linked to exactly one Person.

    Attributes:
        rfid_uid: Hex-encoded card UID as read by MFRC522.
        person_id: Foreign key to the owning Person.
        status: Current card status.
        enrolled_at: UTC Unix epoch timestamp of card binding.
    """

    rfid_uid: str
    person_id: str
    status: UserStatus = UserStatus.ACTIVE
    enrolled_at: float = field(default_factory=time.time)


@dataclass(frozen=True)
class FaceSample:
    """A single captured face training sample.

    Attributes:
        sample_id: UUIDv4 unique identifier.
        person_id: Foreign key to the subject Person.
        file_path: Relative path to the normalized PNG crop on disk.
        captured_at: UTC Unix epoch timestamp of capture.
    """

    sample_id: str
    person_id: str
    file_path: str
    captured_at: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Session Entities
# ---------------------------------------------------------------------------


@dataclass
class AccessSession:
    """A single access-control verification session.

    Mutable: ``state`` and ``match_count`` are updated as the FSM progresses
    through verification frames. All other fields are fixed at session creation.

    Attributes:
        session_id: UUIDv4 session identifier.
        card_uid: The RFID UID that initiated this session.
        expected_person_id: The resolved card owner from IdentityRepository.
        started_at: Monotonic timestamp at session creation.
        deadline: Monotonic timestamp beyond which the session is timed out.
        state: Current FSM state string.
        match_count: Consecutive positive biometric matches accumulated.
    """

    session_id: str
    card_uid: str
    expected_person_id: str
    started_at: float
    deadline: float
    state: str = "VERIFYING"
    match_count: int = 0

    def is_active(self, now_monotonic: float) -> bool:
        """Return True if the session is still within its verification window."""
        return self.state == "VERIFYING" and now_monotonic < self.deadline


# ---------------------------------------------------------------------------
# Audit Event (Immutable)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AccessEvent:
    """An immutable audit record of a single authorization evaluation.

    Attributes:
        event_id: UUIDv4 unique audit event identifier.
        session_id: The session that produced this event.
        timestamp: UTC Unix epoch time of the evaluation.
        card_uid: The RFID UID that was presented.
        expected_person_id: The card owner (None if card unknown).
        observed_person_id: The face identity recognized (None if no face).
        observed_distance: Raw biometric distance/similarity score.
        decision: "GRANT" or "DENY".
        reason: Machine-readable ReasonCode string value.
    """

    event_id: str
    session_id: str
    timestamp: float
    card_uid: str
    expected_person_id: str | None
    observed_person_id: str | None
    observed_distance: float | None
    decision: str
    reason: str


# ---------------------------------------------------------------------------
# System Configuration (Immutable Value Object)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SystemConfig:
    """Runtime configuration parameters with validated defaults.

    All values may be overridden via environment variables or a local ``.env`` file.

    Reference: DOC-07-CONFIG (docs/07-operations/configuration.md)
    """

    verification_window_s: float = 10.0
    door_hold_s: float = 3.0
    required_consistent_matches: int = 3
    lbph_threshold: float = 65.0
    sface_threshold: float = 0.363
    camera_index: int = 0
    serial_port: str = "/dev/ttyUSB0"
    serial_baud: int = 115200
    heartbeat_interval_s: float = 1.0
    heartbeat_timeout_s: float = 3.0
    allow_multiple_faces: bool = False
