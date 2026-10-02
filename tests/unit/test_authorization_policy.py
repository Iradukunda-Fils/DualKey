# SPDX-License-Identifier: MIT
"""Exhaustive truth-table unit tests for AuthorizationPolicy.

Tests every branch and boundary condition of the canonical authorization rule:
    1. Timeout (deadline exceeded)
    2. No face detected (biometric is None or face_count == 0)
    3. Multiple faces (ambiguity rejection)
    4. Low confidence (distance > threshold)
    5. Face mismatch (wrong person recognized)
    6. Stable-match gate (incremental count → GRANT at N)
    7. Fail-closed default behavior

Reference: DOC-03-AUTH (docs/03-design/authorization-engine.md)
"""

from __future__ import annotations

import pytest

from app.domain.decisions import (
    AccessDecision,
    AuthorizationPolicy,
    BiometricFrameResult,
    DecisionResult,
)
from app.domain.models import AccessSession
from app.domain.reason_codes import ReasonCode

# ---------------------------------------------------------------------------
# Test Fixtures — factory helpers for building test sessions and biometrics
# ---------------------------------------------------------------------------


def _make_session(
    *,
    session_id: str = "session-001",
    card_uid: str = "AABBCCDD",
    expected_person_id: str = "person-alice",
    started_at: float = 100.0,
    deadline: float = 110.0,
    state: str = "VERIFYING",
    match_count: int = 0,
) -> AccessSession:
    """Create a fresh AccessSession with sensible defaults."""
    return AccessSession(
        session_id=session_id,
        card_uid=card_uid,
        expected_person_id=expected_person_id,
        started_at=started_at,
        deadline=deadline,
        state=state,
        match_count=match_count,
    )


def _make_biometric(
    *,
    face_count: int = 1,
    recognized_person_id: str | None = "person-alice",
    distance: float = 40.0,
) -> BiometricFrameResult:
    """Create a BiometricFrameResult with sensible defaults."""
    return BiometricFrameResult(
        face_count=face_count,
        recognized_person_id=recognized_person_id,
        distance=distance,
    )


# Default policy parameters
THRESHOLD = 65.0
REQUIRED_MATCHES = 3


class TestTimeoutEnforcement:
    """Step 1: Monotonic deadline check — time is non-negotiable."""

    def test_deny_when_exactly_at_deadline(self) -> None:
        session = _make_session(deadline=110.0)
        biometric = _make_biometric()

        decision = AuthorizationPolicy.evaluate(
            session, biometric, now_monotonic=110.0, threshold=THRESHOLD
        )

        assert decision.result == DecisionResult.DENY
        assert decision.reason == ReasonCode.TIMEOUT
        assert session.match_count == 0  # No increment on timeout

    def test_deny_when_past_deadline(self) -> None:
        session = _make_session(deadline=110.0)
        biometric = _make_biometric()

        decision = AuthorizationPolicy.evaluate(
            session, biometric, now_monotonic=115.0, threshold=THRESHOLD
        )

        assert decision.result == DecisionResult.DENY
        assert decision.reason == ReasonCode.TIMEOUT

    def test_timeout_takes_priority_over_valid_biometric(self) -> None:
        """Even a perfect biometric match is rejected if the deadline passed."""
        session = _make_session(deadline=110.0, match_count=2)
        biometric = _make_biometric(distance=10.0)  # Perfect match

        decision = AuthorizationPolicy.evaluate(
            session, biometric, now_monotonic=110.0, threshold=THRESHOLD
        )

        assert decision.result == DecisionResult.DENY
        assert decision.reason == ReasonCode.TIMEOUT
        assert session.match_count == 2  # Unchanged


class TestNoFaceDetected:
    """Step 2: Missing biometric data — CONTINUE scanning."""

    def test_continue_when_biometric_is_none(self) -> None:
        session = _make_session()

        decision = AuthorizationPolicy.evaluate(
            session, biometric=None, now_monotonic=105.0, threshold=THRESHOLD
        )

        assert decision.result == DecisionResult.CONTINUE
        assert decision.reason == ReasonCode.FACE_NOT_FOUND

    def test_continue_when_face_count_is_zero(self) -> None:
        session = _make_session()
        biometric = _make_biometric(face_count=0)

        decision = AuthorizationPolicy.evaluate(
            session, biometric, now_monotonic=105.0, threshold=THRESHOLD
        )

        assert decision.result == DecisionResult.CONTINUE
        assert decision.reason == ReasonCode.FACE_NOT_FOUND


class TestMultipleFaces:
    """Step 3: Ambiguous scene — immediate DENY."""

    def test_deny_when_two_faces_detected(self) -> None:
        session = _make_session()
        biometric = _make_biometric(face_count=2)

        decision = AuthorizationPolicy.evaluate(
            session, biometric, now_monotonic=105.0, threshold=THRESHOLD
        )

        assert decision.result == DecisionResult.DENY
        assert decision.reason == ReasonCode.MULTIPLE_FACES

    def test_deny_when_many_faces_detected(self) -> None:
        session = _make_session()
        biometric = _make_biometric(face_count=5)

        decision = AuthorizationPolicy.evaluate(
            session, biometric, now_monotonic=105.0, threshold=THRESHOLD
        )

        assert decision.result == DecisionResult.DENY
        assert decision.reason == ReasonCode.MULTIPLE_FACES


class TestLowConfidence:
    """Step 4: Distance exceeds threshold — CONTINUE scanning."""

    def test_continue_when_distance_exceeds_threshold(self) -> None:
        session = _make_session()
        biometric = _make_biometric(distance=70.0)  # > 65.0

        decision = AuthorizationPolicy.evaluate(
            session, biometric, now_monotonic=105.0, threshold=THRESHOLD
        )

        assert decision.result == DecisionResult.CONTINUE
        assert decision.reason == ReasonCode.LOW_CONFIDENCE
        assert decision.distance == 70.0
        assert session.match_count == 0  # No increment

    def test_continue_when_distance_barely_exceeds_threshold(self) -> None:
        session = _make_session()
        biometric = _make_biometric(distance=65.1)

        decision = AuthorizationPolicy.evaluate(
            session, biometric, now_monotonic=105.0, threshold=THRESHOLD
        )

        assert decision.result == DecisionResult.CONTINUE
        assert decision.reason == ReasonCode.LOW_CONFIDENCE


class TestFaceMismatch:
    """Step 5: Identity binding violation — immediate DENY."""

    def test_deny_when_wrong_person_recognized(self) -> None:
        session = _make_session(expected_person_id="person-alice")
        biometric = _make_biometric(
            recognized_person_id="person-bob",
            distance=30.0,  # Good confidence, wrong person
        )

        decision = AuthorizationPolicy.evaluate(
            session, biometric, now_monotonic=105.0, threshold=THRESHOLD
        )

        assert decision.result == DecisionResult.DENY
        assert decision.reason == ReasonCode.FACE_MISMATCH
        assert decision.observed_person_id == "person-bob"
        assert decision.expected_person_id == "person-alice"

    def test_deny_when_recognized_person_is_none_and_expected_is_set(self) -> None:
        """A None recognized_person_id != expected_person_id → mismatch."""
        session = _make_session(expected_person_id="person-alice")
        biometric = _make_biometric(recognized_person_id=None, distance=30.0)

        decision = AuthorizationPolicy.evaluate(
            session, biometric, now_monotonic=105.0, threshold=THRESHOLD
        )

        assert decision.result == DecisionResult.DENY
        assert decision.reason == ReasonCode.FACE_MISMATCH


class TestStableMatchGate:
    """Step 6: Consecutive match accumulation → GRANT at threshold."""

    def test_continue_on_first_match(self) -> None:
        session = _make_session(match_count=0)
        biometric = _make_biometric(distance=40.0)

        decision = AuthorizationPolicy.evaluate(
            session, biometric, now_monotonic=105.0, threshold=THRESHOLD
        )

        assert decision.result == DecisionResult.CONTINUE
        assert decision.reason == ReasonCode.MATCH_IN_PROGRESS
        assert session.match_count == 1

    def test_continue_on_second_match(self) -> None:
        session = _make_session(match_count=1)
        biometric = _make_biometric(distance=40.0)

        decision = AuthorizationPolicy.evaluate(
            session, biometric, now_monotonic=105.0, threshold=THRESHOLD
        )

        assert decision.result == DecisionResult.CONTINUE
        assert decision.reason == ReasonCode.MATCH_IN_PROGRESS
        assert session.match_count == 2

    def test_grant_on_third_match(self) -> None:
        session = _make_session(match_count=2)
        biometric = _make_biometric(distance=40.0)

        decision = AuthorizationPolicy.evaluate(
            session, biometric, now_monotonic=105.0, threshold=THRESHOLD
        )

        assert decision.result == DecisionResult.GRANT
        assert decision.reason == ReasonCode.MATCHED_OWNER
        assert session.match_count == 3

    def test_grant_with_custom_required_matches(self) -> None:
        session = _make_session(match_count=0)
        biometric = _make_biometric(distance=40.0)

        # Require only 1 match
        decision = AuthorizationPolicy.evaluate(
            session,
            biometric,
            now_monotonic=105.0,
            threshold=THRESHOLD,
            required_matches=1,
        )

        assert decision.result == DecisionResult.GRANT
        assert decision.reason == ReasonCode.MATCHED_OWNER
        assert session.match_count == 1

    def test_grant_at_exact_threshold_distance(self) -> None:
        """Distance == threshold should pass the confidence gate."""
        session = _make_session(match_count=2)
        biometric = _make_biometric(distance=65.0)  # Exactly at threshold

        decision = AuthorizationPolicy.evaluate(
            session, biometric, now_monotonic=105.0, threshold=THRESHOLD
        )

        assert decision.result == DecisionResult.GRANT
        assert decision.reason == ReasonCode.MATCHED_OWNER


class TestFullSequentialWorkflow:
    """End-to-end sequential evaluation simulating a real session."""

    def test_three_frame_grant_sequence(self) -> None:
        """Simulate 3 consecutive good frames → GRANT."""
        session = _make_session()
        biometric = _make_biometric(distance=40.0)

        # Frame 1 → CONTINUE
        d1 = AuthorizationPolicy.evaluate(
            session, biometric, now_monotonic=101.0, threshold=THRESHOLD
        )
        assert d1.result == DecisionResult.CONTINUE
        assert d1.reason == ReasonCode.MATCH_IN_PROGRESS

        # Frame 2 → CONTINUE
        d2 = AuthorizationPolicy.evaluate(
            session, biometric, now_monotonic=102.0, threshold=THRESHOLD
        )
        assert d2.result == DecisionResult.CONTINUE
        assert d2.reason == ReasonCode.MATCH_IN_PROGRESS

        # Frame 3 → GRANT
        d3 = AuthorizationPolicy.evaluate(
            session, biometric, now_monotonic=103.0, threshold=THRESHOLD
        )
        assert d3.result == DecisionResult.GRANT
        assert d3.reason == ReasonCode.MATCHED_OWNER

    def test_two_good_frames_then_mismatch_denies(self) -> None:
        """2 good frames, then a wrong face → immediate DENY."""
        session = _make_session()
        good_bio = _make_biometric(distance=40.0)
        bad_bio = _make_biometric(recognized_person_id="person-bob", distance=30.0)

        AuthorizationPolicy.evaluate(
            session, good_bio, now_monotonic=101.0, threshold=THRESHOLD
        )
        AuthorizationPolicy.evaluate(
            session, good_bio, now_monotonic=102.0, threshold=THRESHOLD
        )
        assert session.match_count == 2

        # Wrong face appears → DENY
        d3 = AuthorizationPolicy.evaluate(
            session, bad_bio, now_monotonic=103.0, threshold=THRESHOLD
        )
        assert d3.result == DecisionResult.DENY
        assert d3.reason == ReasonCode.FACE_MISMATCH

    def test_interleaved_no_face_preserves_count(self) -> None:
        """Good frame, no-face frame, good frame — count should grow."""
        session = _make_session()
        good_bio = _make_biometric(distance=40.0)
        no_face = _make_biometric(face_count=0)

        # Frame 1: good → count=1
        AuthorizationPolicy.evaluate(
            session, good_bio, now_monotonic=101.0, threshold=THRESHOLD
        )
        assert session.match_count == 1

        # Frame 2: no face → CONTINUE, count unchanged
        d2 = AuthorizationPolicy.evaluate(
            session, no_face, now_monotonic=102.0, threshold=THRESHOLD
        )
        assert d2.result == DecisionResult.CONTINUE
        assert d2.reason == ReasonCode.FACE_NOT_FOUND
        assert session.match_count == 1  # Preserved

        # Frame 3: good → count=2
        AuthorizationPolicy.evaluate(
            session, good_bio, now_monotonic=103.0, threshold=THRESHOLD
        )
        assert session.match_count == 2


class TestAccessDecisionDataIntegrity:
    """Verify that AccessDecision carries correct metadata."""

    def test_grant_decision_carries_all_fields(self) -> None:
        session = _make_session(match_count=2, expected_person_id="person-alice")
        biometric = _make_biometric(
            recognized_person_id="person-alice", distance=35.5
        )

        decision = AuthorizationPolicy.evaluate(
            session, biometric, now_monotonic=105.0, threshold=THRESHOLD
        )

        assert decision.result == DecisionResult.GRANT
        assert decision.reason == ReasonCode.MATCHED_OWNER
        assert decision.session_id == "session-001"
        assert decision.expected_person_id == "person-alice"
        assert decision.observed_person_id == "person-alice"
        assert decision.distance == 35.5

    def test_deny_timeout_has_no_biometric_data(self) -> None:
        session = _make_session(deadline=110.0)
        biometric = _make_biometric()

        decision = AuthorizationPolicy.evaluate(
            session, biometric, now_monotonic=110.0, threshold=THRESHOLD
        )

        assert decision.observed_person_id is None
        assert decision.distance is None


class TestEdgeCases:
    """Boundary conditions and unusual inputs."""

    def test_zero_required_matches_grants_immediately(self) -> None:
        """Edge case: if required_matches=0, first good frame grants.

        Note: The match_count is incremented to 1 before comparing to 0,
        so this still requires one positive frame (which is correct behavior).
        """
        session = _make_session(match_count=0)
        biometric = _make_biometric(distance=40.0)

        decision = AuthorizationPolicy.evaluate(
            session,
            biometric,
            now_monotonic=105.0,
            threshold=THRESHOLD,
            required_matches=0,
        )

        # match_count goes 0 → 1, which is >= 0 → GRANT
        assert decision.result == DecisionResult.GRANT

    def test_negative_distance_passes_threshold(self) -> None:
        """Negative distances (if ever produced) should still pass ≤ threshold."""
        session = _make_session(match_count=2)
        biometric = _make_biometric(distance=-1.0)

        decision = AuthorizationPolicy.evaluate(
            session, biometric, now_monotonic=105.0, threshold=THRESHOLD
        )

        assert decision.result == DecisionResult.GRANT

    def test_session_just_before_deadline_allows_evaluation(self) -> None:
        session = _make_session(deadline=110.0, match_count=2)
        biometric = _make_biometric(distance=40.0)

        decision = AuthorizationPolicy.evaluate(
            session, biometric, now_monotonic=109.999, threshold=THRESHOLD
        )

        assert decision.result == DecisionResult.GRANT

    def test_frozen_access_decision_is_immutable(self) -> None:
        decision = AccessDecision(
            result=DecisionResult.DENY,
            reason=ReasonCode.TIMEOUT,
            session_id="s1",
            expected_person_id="p1",
        )

        with pytest.raises(AttributeError):
            decision.result = DecisionResult.GRANT  # type: ignore[misc]

    def test_frozen_biometric_is_immutable(self) -> None:
        bio = BiometricFrameResult(
            face_count=1, recognized_person_id="p1", distance=10.0
        )

        with pytest.raises(AttributeError):
            bio.face_count = 2  # type: ignore[misc]
