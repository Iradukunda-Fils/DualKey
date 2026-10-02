# SPDX-License-Identifier: MIT
"""Integration tests for authorization combinations.

Validates Phase 12 item 5 requirements for authorization matrix.
"""

from __future__ import annotations

import sqlite3
from typing import Any

import pytest

from app.adapters.sqlite_repositories import (
    SqliteEventRepository,
    SqliteIdentityRepository,
    create_connection,
)
from app.application.access_controller import AccessController
from app.application.event_logger import EventLogger
from app.application.health_service import HealthService
from app.domain.models import Person, RFIDCard, SystemConfig, UserStatus
from app.domain.states import SessionState
from app.ports.detector import DetectedFace
from app.ports.device_transport import DeviceEvent
from app.ports.recognizer import RecognitionResult
from tests.integration.test_access_workflow import (
    FakeCamera,
    FakeClock,
    FakeDetector,
    FakeRecognizer,
    FakeTransport,
)


@pytest.fixture
def conn() -> sqlite3.Connection:
    return create_connection(":memory:")


@pytest.fixture
def setup(conn: sqlite3.Connection) -> dict[str, Any]:
    config = SystemConfig(
        verification_window_s=10.0,
        required_consistent_matches=3,
        lbph_threshold=65.0,
    )

    identity_repo = SqliteIdentityRepository(conn)
    event_repo = SqliteEventRepository(conn)

    alice = Person(
        person_id="alice-001",
        display_name="Alice",
        face_label=0,
        status=UserStatus.ACTIVE,
        created_at=1000.0,
    )
    bob = Person(
        person_id="bob-002",
        display_name="Bob",
        face_label=1,
        status=UserStatus.ACTIVE,
        created_at=1000.0,
    )
    identity_repo.create_person(alice)
    identity_repo.create_person(bob)

    identity_repo.bind_card(RFIDCard(
        rfid_uid="AABBCCDD",
        person_id="alice-001",
        enrolled_at=1000.0,
    ))
    identity_repo.bind_card(RFIDCard(
        rfid_uid="11223344",
        person_id="bob-002",
        enrolled_at=1000.0,
    ))

    clock = FakeClock(start=100.0)
    camera = FakeCamera()
    detector = FakeDetector()
    recognizer = FakeRecognizer(default_person="alice-001")
    transport = FakeTransport()

    event_logger = EventLogger(event_repo)
    health_service = HealthService(
        camera=camera,
        transport=transport,
        clock=clock,
        heartbeat_timeout_s=3.0,
    )
    health_service.record_heartbeat()

    controller = AccessController(
        config=config,
        identity_repo=identity_repo,
        transport=transport,
        camera=camera,
        detector=detector,
        recognizer=recognizer,
        clock=clock,
        event_logger=event_logger,
        health_service=health_service,
    )

    return {
        "controller": controller,
        "transport": transport,
        "clock": clock,
        "camera": camera,
        "detector": detector,
        "recognizer": recognizer,
    }


def inject_heartbeat(transport: FakeTransport, clock: FakeClock) -> None:
    transport.inject_event(DeviceEvent(
        event_type="heartbeat",
        payload={"uptime_ms": int(clock.time * 1000)},
        event_id=f"hb-{clock.time}",
    ))


class TestAuthorizationMatrix:
    def test_correct_rfid_correct_face_grants(self, setup: dict[str, Any]) -> None:
        controller: AccessController = setup["controller"]
        transport: FakeTransport = setup["transport"]
        clock: FakeClock = setup["clock"]

        transport.inject_rfid("AABBCCDD")
        controller.tick()

        for _ in range(3):
            clock.advance(1.0)
            inject_heartbeat(transport, clock)
            controller.tick()

        assert controller.state == SessionState.IDLE
        assert transport.sent_commands[-1].decision == "grant"

    def test_correct_rfid_wrong_face_denies(self, setup: dict[str, Any]) -> None:
        controller: AccessController = setup["controller"]
        transport: FakeTransport = setup["transport"]
        clock: FakeClock = setup["clock"]
        recognizer: FakeRecognizer = setup["recognizer"]

        recognizer.set_results([
            RecognitionResult(
                identity="bob-002", score=30.0, is_match=True,
                confidence_level="HIGH", model_id="lbph",
                model_version="1",
            )
        ])

        transport.inject_rfid("AABBCCDD")
        controller.tick()

        clock.advance(1.0)
        inject_heartbeat(transport, clock)
        controller.tick()

        assert controller.state == SessionState.IDLE
        assert transport.sent_commands[-1].decision == "deny"
        assert transport.sent_commands[-1].reason == "FACE_MISMATCH"

    def test_correct_rfid_unknown_face_denies(self, setup: dict[str, Any]) -> None:
        """Correct card + unrecognized face -> DENY (FACE_MISMATCH).

        When recognition returns is_match=False with identity=None,
        the policy sees recognized_person_id=None != expected alice-001
        and immediately denies with FACE_MISMATCH.
        """
        controller: AccessController = setup["controller"]
        transport: FakeTransport = setup["transport"]
        clock: FakeClock = setup["clock"]
        recognizer: FakeRecognizer = setup["recognizer"]

        recognizer.set_results([
            RecognitionResult(
                identity=None, score=100.0, is_match=False,
                confidence_level="LOW", model_id="lbph",
                model_version="1",
            )
        ] * 5)

        transport.inject_rfid("AABBCCDD")
        controller.tick()

        clock.advance(1.0)
        inject_heartbeat(transport, clock)
        controller.tick()

        assert controller.state == SessionState.IDLE
        assert transport.sent_commands[-1].decision == "deny"
        assert transport.sent_commands[-1].reason == "FACE_MISMATCH"

    def test_unknown_rfid_correct_face_denies(self, setup: dict[str, Any]) -> None:
        controller: AccessController = setup["controller"]
        transport: FakeTransport = setup["transport"]

        transport.inject_rfid("99999999")
        controller.tick()

        assert controller.state == SessionState.IDLE
        assert transport.sent_commands[-1].decision == "deny"
        assert transport.sent_commands[-1].reason == "UNKNOWN_RFID"

    def test_unknown_rfid_wrong_face_denies(self, setup: dict[str, Any]) -> None:
        controller: AccessController = setup["controller"]
        transport: FakeTransport = setup["transport"]

        transport.inject_rfid("88888888")
        controller.tick()

        assert controller.state == SessionState.IDLE
        assert transport.sent_commands[-1].decision == "deny"
        assert transport.sent_commands[-1].reason == "UNKNOWN_RFID"

    def test_correct_rfid_no_face_timeout(self, setup: dict[str, Any]) -> None:
        controller: AccessController = setup["controller"]
        transport: FakeTransport = setup["transport"]
        clock: FakeClock = setup["clock"]
        detector: FakeDetector = setup["detector"]

        detector.set_results([[] for _ in range(15)])

        transport.inject_rfid("AABBCCDD")
        controller.tick()

        for _ in range(11):
            clock.advance(1.0)
            inject_heartbeat(transport, clock)
            controller.tick()
            if controller.state == SessionState.IDLE:
                break

        assert controller.state == SessionState.IDLE
        assert transport.sent_commands[-1].decision == "deny"
        assert transport.sent_commands[-1].reason == "TIMEOUT"

    def test_correct_rfid_multiple_faces_denies(self, setup: dict[str, Any]) -> None:
        controller: AccessController = setup["controller"]
        transport: FakeTransport = setup["transport"]
        clock: FakeClock = setup["clock"]
        detector: FakeDetector = setup["detector"]

        detector.set_results([[
            DetectedFace(bbox=(10,10,20,20), confidence=1.0),
            DetectedFace(bbox=(40,40,20,20), confidence=1.0)
        ]])

        transport.inject_rfid("AABBCCDD")
        controller.tick()

        clock.advance(1.0)
        inject_heartbeat(transport, clock)
        controller.tick()

        assert controller.state == SessionState.IDLE
        assert transport.sent_commands[-1].decision == "deny"
        assert transport.sent_commands[-1].reason == "MULTIPLE_FACES"

    def test_correct_rfid_face_after_timeout_denies(self, setup: dict[str, Any]) -> None:
        controller: AccessController = setup["controller"]
        transport: FakeTransport = setup["transport"]
        clock: FakeClock = setup["clock"]
        detector: FakeDetector = setup["detector"]
        recognizer: FakeRecognizer = setup["recognizer"]

        transport.inject_rfid("AABBCCDD")
        controller.tick()

        detector.set_results([[] for _ in range(10)])

        for _ in range(10):
            clock.advance(1.0)
            inject_heartbeat(transport, clock)
            controller.tick()

        # Now 10 seconds have passed, one more tick with a face should result in timeout, not grant
        res_alice = RecognitionResult(
            identity="alice-001", score=30.0, is_match=True,
            confidence_level="HIGH", model_id="lbph", model_version="1"
        )
        recognizer.set_results([res_alice])
        detector.set_results([[DetectedFace(bbox=(10,10,20,20), confidence=1.0)]])

        clock.advance(1.0)
        inject_heartbeat(transport, clock)
        controller.tick()

        assert controller.state == SessionState.IDLE
        assert transport.sent_commands[-1].decision == "deny"
        assert transport.sent_commands[-1].reason == "TIMEOUT"
