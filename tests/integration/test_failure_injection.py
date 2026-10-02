# SPDX-License-Identifier: MIT
"""Integration tests for failure injection modes.

Validates Phase 12 item 7 requirements for fail-closed behavior.
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
    identity_repo.create_person(alice)
    identity_repo.bind_card(RFIDCard(
        rfid_uid="AABBCCDD",
        person_id="alice-001",
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


class TestFailureInjection:
    def test_camera_returns_none_no_grant(self, setup: dict[str, Any]) -> None:
        controller: AccessController = setup["controller"]
        transport: FakeTransport = setup["transport"]
        clock: FakeClock = setup["clock"]
        camera: FakeCamera = setup["camera"]

        # Simulate camera returning None frames
        camera._frames = []

        def failing_read():  # type: ignore[no-untyped-def]
            return None
        camera.read = failing_read  # type: ignore[assignment]

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

    def test_transport_disconnected_faults(self, setup: dict[str, Any]) -> None:
        controller: AccessController = setup["controller"]
        transport: FakeTransport = setup["transport"]
        clock: FakeClock = setup["clock"]

        transport.inject_rfid("AABBCCDD")
        controller.tick()

        # Simulate link disconnect
        transport._connected = False

        clock.advance(1.0)
        inject_heartbeat(transport, clock)
        controller.tick()

        # Health check detects stale link -> FAULT -> IDLE
        assert controller.state == SessionState.IDLE

    def test_heartbeat_stale_faults(self, setup: dict[str, Any]) -> None:
        controller: AccessController = setup["controller"]
        transport: FakeTransport = setup["transport"]
        clock: FakeClock = setup["clock"]

        transport.inject_rfid("AABBCCDD")
        controller.tick()

        # Advance 4 seconds without heartbeat -> FAULT
        clock.advance(4.0)
        controller.tick()

        assert controller.state == SessionState.IDLE
        assert transport.sent_commands[-1].decision == "deny"
        assert transport.sent_commands[-1].reason == "DEVICE_LINK_ERROR"

    def test_malformed_rfid_event_ignored(self, setup: dict[str, Any]) -> None:
        controller: AccessController = setup["controller"]
        transport: FakeTransport = setup["transport"]

        transport.inject_event(DeviceEvent(event_type="rfid_detected", payload={}, event_id="123"))
        controller.tick()

        assert controller.state == SessionState.IDLE
        assert len(transport.sent_commands) == 0

    def test_session_survives_single_no_face(self, setup: dict[str, Any]) -> None:
        controller: AccessController = setup["controller"]
        transport: FakeTransport = setup["transport"]
        clock: FakeClock = setup["clock"]
        detector: FakeDetector = setup["detector"]
        recognizer: FakeRecognizer = setup["recognizer"]

        res_alice = RecognitionResult(
            identity="alice-001", score=30.0, is_match=True,
            confidence_level="HIGH", model_id="lbph", model_version="1"
        )

        # 1 good frame, 1 empty, 2 good frames -> grant
        recognizer.set_results([res_alice, res_alice, res_alice])
        detector.set_results([
            [DetectedFace(bbox=(10,10,20,20), confidence=1.0)],
            [],
            [DetectedFace(bbox=(10,10,20,20), confidence=1.0)],
            [DetectedFace(bbox=(10,10,20,20), confidence=1.0)],
        ])

        transport.inject_rfid("AABBCCDD")
        controller.tick()

        for _ in range(4):
            clock.advance(1.0)
            inject_heartbeat(transport, clock)
            controller.tick()

        assert controller.state == SessionState.IDLE
        assert transport.sent_commands[-1].decision == "grant"

    def test_timeout_closes_door(self, setup: dict[str, Any]) -> None:
        controller: AccessController = setup["controller"]
        transport: FakeTransport = setup["transport"]
        clock: FakeClock = setup["clock"]
        detector: FakeDetector = setup["detector"]

        detector.set_results([[] for _ in range(15)])

        transport.inject_rfid("AABBCCDD")
        controller.tick()
        assert controller.state == SessionState.VERIFYING

        for _ in range(11):
            clock.advance(1.0)
            inject_heartbeat(transport, clock)
            controller.tick()

        assert controller.state == SessionState.IDLE
        assert transport.sent_commands[-1].decision == "deny"
        assert transport.sent_commands[-1].reason == "TIMEOUT"

    def test_idle_state_is_safe(self, setup: dict[str, Any]) -> None:
        controller: AccessController = setup["controller"]
        transport: FakeTransport = setup["transport"]
        clock: FakeClock = setup["clock"]

        assert controller.state == SessionState.IDLE

        for _ in range(5):
            clock.advance(1.0)
            inject_heartbeat(transport, clock)
            controller.tick()

        assert controller.state == SessionState.IDLE
        assert len(transport.sent_commands) == 0
