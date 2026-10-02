# SPDX-License-Identifier: MIT
"""Pure, deterministic authorization policy — the heart of DualKey.

This module contains the canonical multi-factor authorization rule that
governs every physical access decision. It is a pure function: no I/O,
no side effects beyond incrementing the session match counter, and no
imports of infrastructure libraries.

The policy enforces the fail-closed invariant: every edge case, indeterminate
biometric signal, sensor error, or timeout defaults unconditionally to DENY.

Reference: DOC-03-AUTH (docs/03-design/authorization-engine.md)

Canonical Authorization Formula:
    GRANT iff:
        card_valid
        AND (t_now < t_deadline)
        AND (face_count == 1)
        AND (distance <= threshold)
        AND (person_recognized == person_owner)
        AND (match_count >= N_required)
    Otherwise → DENY (fail-closed default)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum, unique

from app.domain.models import AccessSession
from app.domain.reason_codes import ReasonCode


@unique
class DecisionResult(StrEnum):
    """Outcome of a single authorization policy evaluation.

    Attributes:
        GRANT: All conditions met — command door to open.
        DENY: Hard rejection — session terminates with denial.
        CONTINUE: Transient state — keep acquiring frames within window.
    """

    GRANT = "grant"
    DENY = "deny"
    CONTINUE = "continue"


@dataclass(frozen=True)
class AccessDecision:
    """Immutable value object representing one policy evaluation result.

    Attributes:
        result: Terminal or transient decision outcome.
        reason: Machine-readable reason code for audit logging.
        session_id: The session being evaluated.
        expected_person_id: The card owner's identity.
        observed_person_id: The face identity recognized (if any).
        distance: Raw biometric distance/similarity score (if available).
    """

    result: DecisionResult
    reason: ReasonCode
    session_id: str
    expected_person_id: str
    observed_person_id: str | None = None
    distance: float | None = None


@dataclass(frozen=True)
class BiometricFrameResult:
    """A single frame's face-detection and recognition output.

    This is a pure data transfer object carrying the results of one camera
    frame through the detector → recognizer pipeline, without any coupling
    to OpenCV types.

    Attributes:
        face_count: Number of faces detected in this frame.
        recognized_person_id: Identity resolved by the recognizer (if any).
        distance: Raw distance metric (LBPH chi-square) or similarity
                  score (SFace cosine). Interpretation depends on the
                  active recognizer backend.
    """

    face_count: int
    recognized_person_id: str | None
    distance: float


class AuthorizationPolicy:
    """Stateless policy evaluator enforcing the canonical authorization rule.

    This class contains a single static method that implements a pure,
    side-effect-free evaluation of the multi-factor authorization formula.
    It is designed to be trivially unit-testable via truth-table enumeration.

    Design Decision:
        The policy mutates ``session.match_count`` as an intentional
        in-place counter update. This is the only state modification
        permitted, and it allows the caller to track match progression
        without maintaining a separate counter. The session is passed by
        reference — the caller owns the session lifecycle.
    """

    @staticmethod
    def evaluate(
        session: AccessSession,
        biometric: BiometricFrameResult | None,
        now_monotonic: float,
        threshold: float,
        required_matches: int = 3,
    ) -> AccessDecision:
        """Evaluate the canonical authorization rule for a single frame.

        This function is pure and deterministic: given the same inputs, it
        always produces the same output. It performs zero I/O.

        Args:
            session: The active verification session (mutable match_count).
            biometric: Frame result from the vision pipeline, or None if
                       the camera failed to produce a frame.
            now_monotonic: Current monotonic clock reading in seconds.
            threshold: Maximum acceptable biometric distance. For LBPH this
                       is an upper bound (chi-square ≤ threshold). For SFace,
                       the caller must invert the comparison before calling.
            required_matches: Number of consecutive positive matches needed
                              to transition from CONTINUE to GRANT.

        Returns:
            An immutable AccessDecision with the evaluation outcome.
        """
        # 1. Enforce monotonic deadline — time is non-negotiable
        if now_monotonic >= session.deadline:
            return AccessDecision(
                result=DecisionResult.DENY,
                reason=ReasonCode.TIMEOUT,
                session_id=session.session_id,
                expected_person_id=session.expected_person_id,
            )

        # 2. No biometric data — camera may have failed or no face present
        if biometric is None or biometric.face_count == 0:
            return AccessDecision(
                result=DecisionResult.CONTINUE,
                reason=ReasonCode.FACE_NOT_FOUND,
                session_id=session.session_id,
                expected_person_id=session.expected_person_id,
            )

        # 3. Ambiguous scene — multiple faces violate single-person invariant
        if biometric.face_count > 1:
            return AccessDecision(
                result=DecisionResult.DENY,
                reason=ReasonCode.MULTIPLE_FACES,
                session_id=session.session_id,
                expected_person_id=session.expected_person_id,
            )

        # 4. Confidence gate — distance exceeds calibrated threshold
        if biometric.distance > threshold:
            return AccessDecision(
                result=DecisionResult.CONTINUE,
                reason=ReasonCode.LOW_CONFIDENCE,
                session_id=session.session_id,
                expected_person_id=session.expected_person_id,
                observed_person_id=biometric.recognized_person_id,
                distance=biometric.distance,
            )

        # 5. Identity binding — does the recognized face match the card owner?
        if biometric.recognized_person_id != session.expected_person_id:
            return AccessDecision(
                result=DecisionResult.DENY,
                reason=ReasonCode.FACE_MISMATCH,
                session_id=session.session_id,
                expected_person_id=session.expected_person_id,
                observed_person_id=biometric.recognized_person_id,
                distance=biometric.distance,
            )

        # 6. Stable-match gate — accumulate consecutive positive matches
        session.match_count += 1
        if session.match_count >= required_matches:
            return AccessDecision(
                result=DecisionResult.GRANT,
                reason=ReasonCode.MATCHED_OWNER,
                session_id=session.session_id,
                expected_person_id=session.expected_person_id,
                observed_person_id=biometric.recognized_person_id,
                distance=biometric.distance,
            )

        # Not enough consecutive matches yet — keep scanning
        return AccessDecision(
            result=DecisionResult.CONTINUE,
            reason=ReasonCode.MATCH_IN_PROGRESS,
            session_id=session.session_id,
            expected_person_id=session.expected_person_id,
            observed_person_id=biometric.recognized_person_id,
            distance=biometric.distance,
        )
