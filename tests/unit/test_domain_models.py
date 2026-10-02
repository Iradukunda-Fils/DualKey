# SPDX-License-Identifier: MIT
"""Unit tests for domain models — immutability, defaults, and invariants."""

from __future__ import annotations

import pytest

from app.domain.models import (
    AccessEvent,
    AccessSession,
    FaceSample,
    Person,
    RFIDCard,
    SystemConfig,
    UserStatus,
)
from app.domain.reason_codes import ReasonCode
from app.domain.states import SessionState


class TestPerson:
    """Tests for the Person frozen dataclass."""

    def test_default_status_is_active(self) -> None:
        p = Person(person_id="p1", display_name="Alice", face_label=0)
        assert p.status == UserStatus.ACTIVE

    def test_frozen_person_rejects_mutation(self) -> None:
        p = Person(person_id="p1", display_name="Alice", face_label=0)
        with pytest.raises(AttributeError):
            p.display_name = "Bob"  # type: ignore[misc]

    def test_person_equality_by_fields(self) -> None:
        p1 = Person(
            person_id="p1", display_name="Alice", face_label=0, created_at=1000.0
        )
        p2 = Person(
            person_id="p1", display_name="Alice", face_label=0, created_at=1000.0
        )
        assert p1 == p2

    def test_revoked_status(self) -> None:
        p = Person(
            person_id="p1",
            display_name="Alice",
            face_label=0,
            status=UserStatus.REVOKED,
        )
        assert p.status == UserStatus.REVOKED


class TestRFIDCard:
    """Tests for the RFIDCard frozen dataclass."""

    def test_card_creation(self) -> None:
        c = RFIDCard(rfid_uid="AABBCCDD", person_id="p1")
        assert c.rfid_uid == "AABBCCDD"
        assert c.person_id == "p1"
        assert c.status == UserStatus.ACTIVE

    def test_frozen_card_rejects_mutation(self) -> None:
        c = RFIDCard(rfid_uid="AABBCCDD", person_id="p1")
        with pytest.raises(AttributeError):
            c.rfid_uid = "11223344"  # type: ignore[misc]


class TestFaceSample:
    """Tests for the FaceSample frozen dataclass."""

    def test_sample_creation(self) -> None:
        s = FaceSample(sample_id="s1", person_id="p1", file_path="data/faces/p1/01.png")
        assert s.file_path == "data/faces/p1/01.png"

    def test_frozen_sample_rejects_mutation(self) -> None:
        s = FaceSample(sample_id="s1", person_id="p1", file_path="img.png")
        with pytest.raises(AttributeError):
            s.file_path = "other.png"  # type: ignore[misc]


class TestAccessSession:
    """Tests for the mutable AccessSession dataclass."""

    def test_default_state_is_verifying(self) -> None:
        sess = AccessSession(
            session_id="s1",
            card_uid="AABB",
            expected_person_id="p1",
            started_at=100.0,
            deadline=110.0,
        )
        assert sess.state == "VERIFYING"
        assert sess.match_count == 0

    def test_is_active_within_deadline(self) -> None:
        sess = AccessSession(
            session_id="s1",
            card_uid="AABB",
            expected_person_id="p1",
            started_at=100.0,
            deadline=110.0,
        )
        assert sess.is_active(105.0) is True

    def test_is_not_active_at_deadline(self) -> None:
        sess = AccessSession(
            session_id="s1",
            card_uid="AABB",
            expected_person_id="p1",
            started_at=100.0,
            deadline=110.0,
        )
        assert sess.is_active(110.0) is False

    def test_is_not_active_past_deadline(self) -> None:
        sess = AccessSession(
            session_id="s1",
            card_uid="AABB",
            expected_person_id="p1",
            started_at=100.0,
            deadline=110.0,
        )
        assert sess.is_active(115.0) is False

    def test_is_not_active_when_state_is_not_verifying(self) -> None:
        sess = AccessSession(
            session_id="s1",
            card_uid="AABB",
            expected_person_id="p1",
            started_at=100.0,
            deadline=110.0,
            state="GRANTED",
        )
        assert sess.is_active(105.0) is False

    def test_match_count_is_mutable(self) -> None:
        sess = AccessSession(
            session_id="s1",
            card_uid="AABB",
            expected_person_id="p1",
            started_at=100.0,
            deadline=110.0,
        )
        sess.match_count += 1
        assert sess.match_count == 1


class TestAccessEvent:
    """Tests for the AccessEvent frozen dataclass."""

    def test_event_creation(self) -> None:
        event = AccessEvent(
            event_id="e1",
            session_id="s1",
            timestamp=1000.0,
            card_uid="AABB",
            expected_person_id="p1",
            observed_person_id="p1",
            observed_distance=40.0,
            decision="GRANT",
            reason="MATCHED_OWNER",
        )
        assert event.decision == "GRANT"
        assert event.reason == "MATCHED_OWNER"

    def test_frozen_event_rejects_mutation(self) -> None:
        event = AccessEvent(
            event_id="e1",
            session_id="s1",
            timestamp=1000.0,
            card_uid="AABB",
            expected_person_id=None,
            observed_person_id=None,
            observed_distance=None,
            decision="DENY",
            reason="UNKNOWN_RFID",
        )
        with pytest.raises(AttributeError):
            event.decision = "GRANT"  # type: ignore[misc]


class TestSystemConfig:
    """Tests for SystemConfig frozen dataclass defaults."""

    def test_default_values(self) -> None:
        cfg = SystemConfig()
        assert cfg.verification_window_s == 10.0
        assert cfg.door_hold_s == 3.0
        assert cfg.required_consistent_matches == 3
        assert cfg.lbph_threshold == 65.0
        assert cfg.sface_threshold == 0.363
        assert cfg.camera_index == 0
        assert cfg.serial_port == "/dev/ttyUSB0"
        assert cfg.serial_baud == 115200
        assert cfg.heartbeat_interval_s == 1.0
        assert cfg.heartbeat_timeout_s == 3.0
        assert cfg.allow_multiple_faces is False

    def test_custom_values(self) -> None:
        cfg = SystemConfig(
            verification_window_s=15.0,
            required_consistent_matches=5,
            lbph_threshold=50.0,
        )
        assert cfg.verification_window_s == 15.0
        assert cfg.required_consistent_matches == 5
        assert cfg.lbph_threshold == 50.0

    def test_frozen_config_rejects_mutation(self) -> None:
        cfg = SystemConfig()
        with pytest.raises(AttributeError):
            cfg.lbph_threshold = 100.0  # type: ignore[misc]


class TestEnums:
    """Tests for UserStatus, SessionState, and ReasonCode enums."""

    def test_user_status_values(self) -> None:
        assert UserStatus.ACTIVE == "ACTIVE"
        assert UserStatus.REVOKED == "REVOKED"

    def test_session_state_values(self) -> None:
        expected = {"IDLE", "CARD_VALIDATING", "VERIFYING", "GRANTED",
                    "DENIED", "TIMEOUT", "FAULT"}
        actual = {s.value for s in SessionState}
        assert actual == expected

    def test_reason_code_values(self) -> None:
        expected = {
            "MATCHED_OWNER", "MATCH_IN_PROGRESS", "FACE_NOT_FOUND",
            "LOW_CONFIDENCE", "UNKNOWN_RFID", "FACE_MISMATCH",
            "MULTIPLE_FACES", "TIMEOUT", "CAMERA_ERROR",
            "DEVICE_LINK_ERROR", "COMMAND_REJECTED", "ACTUATOR_FAILURE",
        }
        actual = {r.value for r in ReasonCode}
        assert actual == expected

    def test_reason_code_is_str_enum(self) -> None:
        """ReasonCode should be usable directly as a string."""
        assert isinstance(ReasonCode.MATCHED_OWNER, str)
        assert ReasonCode.TIMEOUT == "TIMEOUT"

    def test_session_state_is_str_enum(self) -> None:
        assert isinstance(SessionState.IDLE, str)
        assert SessionState.VERIFYING == "VERIFYING"
