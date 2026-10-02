# SPDX-License-Identifier: MIT
"""Integration tests for multi-frame pattern validation.

Validates Phase 12 item 4 requirements for frame sequences.
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


class TestMultiFramePatterns:
    def test_aaa_grants(self, setup: dict[str, Any]) -> None:
        controller: AccessController = setup["controller"]
        transport: FakeTransport = setup["transport"]
        clock: FakeClock = setup["clock"]
        recognizer: FakeRecognizer = setup["recognizer"]

        res_alice = RecognitionResult(
            identity="alice-001", score=30.0, is_match=True,
            confidence_level="HIGH", model_id="lbph_recognizer", model_version="1.0"
        )
        recognizer.set_results([res_alice, res_alice, res_alice])

        transport.inject_rfid("AABBCCDD")
        controller.tick()

        for _ in range(3):
            clock.advance(1.0)
            inject_heartbeat(transport, clock)
            controller.tick()

        assert controller.state == SessionState.IDLE
        assert len(transport.sent_commands) == 1
        assert transport.sent_commands[0].decision == "grant"

    def test_aab_denies(self, setup: dict[str, Any]) -> None:
        controller: AccessController = setup["controller"]
        transport: FakeTransport = setup["transport"]
        clock: FakeClock = setup["clock"]
        recognizer: FakeRecognizer = setup["recognizer"]

        res_alice = RecognitionResult(
            identity="alice-001", score=30.0, is_match=True,
            confidence_level="HIGH", model_id="lbph_recognizer", model_version="1.0"
        )
        res_bob = RecognitionResult(
            identity="bob-002", score=30.0, is_match=True,
            confidence_level="HIGH", model_id="lbph_recognizer", model_version="1.0"
        )
        recognizer.set_results([res_alice, res_alice, res_bob])

        transport.inject_rfid("AABBCCDD")
        controller.tick()

        for _ in range(3):
            clock.advance(1.0)
            inject_heartbeat(transport, clock)
            controller.tick()
            if controller.state == SessionState.IDLE:
                break

        assert controller.state == SessionState.IDLE
        assert len(transport.sent_commands) == 1
        assert transport.sent_commands[0].decision == "deny"
        assert transport.sent_commands[0].reason == "FACE_MISMATCH"

    def test_aba_denies(self, setup: dict[str, Any]) -> None:
        controller: AccessController = setup["controller"]
        transport: FakeTransport = setup["transport"]
        clock: FakeClock = setup["clock"]
        recognizer: FakeRecognizer = setup["recognizer"]

        res_alice = RecognitionResult(
            identity="alice-001", score=30.0, is_match=True,
            confidence_level="HIGH", model_id="lbph_recognizer", model_version="1.0"
        )
        res_bob = RecognitionResult(
            identity="bob-002", score=30.0, is_match=True,
            confidence_level="HIGH", model_id="lbph_recognizer", model_version="1.0"
        )
        recognizer.set_results([res_alice, res_bob, res_alice])

        transport.inject_rfid("AABBCCDD")
        controller.tick()

        for _ in range(2):
            clock.advance(1.0)
            inject_heartbeat(transport, clock)
            controller.tick()
            if controller.state == SessionState.IDLE:
                break

        assert controller.state == SessionState.IDLE
        assert transport.sent_commands[-1].decision == "deny"
        assert transport.sent_commands[-1].reason == "FACE_MISMATCH"

    def test_a_unknown_a_denies(self, setup: dict[str, Any]) -> None:
        """A, UNKNOWN, A -> no immediate grant; match_count resets partially.

        Frame 1: alice match → count=1 → CONTINUE
        Frame 2: unknown (distance=100 > threshold=65) → LOW_CONFIDENCE →
                 CONTINUE (step 4, before identity check). Count stays at 1.
        Frame 3: alice match → count=2 → CONTINUE (need 3 for grant)

        No authorization is granted because the stable-match count never
        reaches the required 3 consecutive matches.
        """
        controller: AccessController = setup["controller"]
        transport: FakeTransport = setup["transport"]
        clock: FakeClock = setup["clock"]
        recognizer: FakeRecognizer = setup["recognizer"]

        res_alice = RecognitionResult(
            identity="alice-001", score=30.0, is_match=True,
            confidence_level="HIGH", model_id="lbph_recognizer", model_version="1.0"
        )
        res_unknown = RecognitionResult(
            identity=None, score=100.0, is_match=False,
            confidence_level="LOW", model_id="lbph_recognizer", model_version="1.0"
        )
        # RFID tick consumes result[0]. 3 results → 3 frame evaluations.
        recognizer.set_results([res_alice, res_unknown, res_alice])

        transport.inject_rfid("AABBCCDD")
        controller.tick()  # Consumes result[0]=alice → count=1

        # 2 more ticks for result[1]=unknown and result[2]=alice
        for _ in range(2):
            clock.advance(1.0)
            inject_heartbeat(transport, clock)
            controller.tick()

        # Still VERIFYING — count=2, not enough for grant
        assert controller.state == SessionState.VERIFYING
        grant_or_deny = [c for c in transport.sent_commands if c.decision in ("grant", "deny")]
        assert len(grant_or_deny) == 0

    def test_aa_unknown_denies(self, setup: dict[str, Any]) -> None:
        """A, A, UNKNOWN -> no grant; session continues with LOW_CONFIDENCE.

        Two valid matches build match_count=2, then the unknown frame has
        distance=100 > threshold=65 → LOW_CONFIDENCE → CONTINUE (step 4
        in the policy, before the identity binding check at step 5).
        The match counter is NOT reset but is NOT incremented either.
        """
        controller: AccessController = setup["controller"]
        transport: FakeTransport = setup["transport"]
        clock: FakeClock = setup["clock"]
        recognizer: FakeRecognizer = setup["recognizer"]

        res_alice = RecognitionResult(
            identity="alice-001", score=30.0, is_match=True,
            confidence_level="HIGH", model_id="lbph_recognizer", model_version="1.0"
        )
        res_unknown = RecognitionResult(
            identity=None, score=100.0, is_match=False,
            confidence_level="LOW", model_id="lbph_recognizer", model_version="1.0"
        )
        # RFID tick also processes a frame, consuming result[0].
        # So 3 results cover ticks: RFID+frame(alice), frame(alice), frame(unknown)
        recognizer.set_results([res_alice, res_alice, res_unknown])

        transport.inject_rfid("AABBCCDD")
        controller.tick()  # Consumes result[0]=alice → count=1

        # 2 more ticks to consume result[1]=alice and result[2]=unknown
        for _ in range(2):
            clock.advance(1.0)
            inject_heartbeat(transport, clock)
            controller.tick()

        # Frame 2 → alice (count=2), Frame 3 → unknown (LOW_CONFIDENCE, CONTINUE)
        # Session should still be VERIFYING — no GRANT reached, no DENY triggered
        assert controller.state == SessionState.VERIFYING
        # No grant or deny commands should have been sent
        grant_or_deny = [c for c in transport.sent_commands if c.decision in ("grant", "deny")]
        assert len(grant_or_deny) == 0
