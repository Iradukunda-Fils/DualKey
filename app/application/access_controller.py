# SPDX-License-Identifier: MIT
"""Access controller -- the central orchestrator of the DualKey access workflow.

Coordinates session lifecycle, biometric evaluation, policy enforcement,
and actuator dispatch. Implements a cooperative tick-based event loop
driven by the host FSM.

Reference: DOC-02-STATE (docs/02-architecture/state-machine.md)
           DOC-03-AUTH (docs/03-design/authorization-engine.md)
           DOC-03-LLD (docs/03-design/low-level-design.md)
"""

from __future__ import annotations

import logging
import uuid

from app.application.event_logger import EventLogger
from app.application.health_service import HealthService
from app.domain.decisions import (
    AuthorizationPolicy,
    BiometricFrameResult,
    DecisionResult,
)
from app.domain.models import AccessSession, SystemConfig
from app.domain.reason_codes import ReasonCode
from app.domain.states import SessionState
from app.ports.camera import CameraPort
from app.ports.clock import ClockPort
from app.ports.detector import DetectedFace, FaceDetectorPort
from app.ports.device_transport import DeviceCommand, DeviceTransportPort
from app.ports.recognizer import FaceRecognizerPort
from app.ports.repositories import IdentityRepository

logger = logging.getLogger(__name__)


class AccessController:
    """Main session workflow and 10.0s monotonic deadline manager.

    Each call to tick() represents one iteration of the cooperative
    event loop. The controller:
        1. Polls the device transport for RFID events
        2. Manages session creation and state transitions
        3. Acquires camera frames and runs the vision pipeline
        4. Evaluates the authorization policy
        5. Dispatches actuator commands
        6. Logs audit events

    Design: the controller never blocks. All I/O is non-blocking or
    bounded by short timeouts configured on the adapters.
    """

    def __init__(
        self,
        config: SystemConfig,
        identity_repo: IdentityRepository,
        transport: DeviceTransportPort,
        camera: CameraPort,
        detector: FaceDetectorPort,
        recognizer: FaceRecognizerPort,
        clock: ClockPort,
        event_logger: EventLogger,
        health_service: HealthService,
    ) -> None:
        self._config = config
        self._identity_repo = identity_repo
        self._transport = transport
        self._camera = camera
        self._detector = detector
        self._recognizer = recognizer
        self._clock = clock
        self._event_logger = event_logger
        self._health = health_service

        self._state = SessionState.IDLE
        self._session: AccessSession | None = None

    @property
    def state(self) -> SessionState:
        """Current FSM state."""
        return self._state

    @property
    def session(self) -> AccessSession | None:
        """Current active session, if any."""
        return self._session

    def tick(self) -> None:
        """Execute one iteration of the cooperative event loop.

        This method is designed to be called repeatedly from the main
        loop. It handles all state transitions non-blockingly.
        """
        # Process incoming device events (heartbeats, RFID taps, command results)
        self._process_device_events()

        if self._state == SessionState.IDLE:
            return  # Nothing to do -- waiting for RFID event

        if self._state == SessionState.VERIFYING:
            self._evaluate_frame()

    def _process_device_events(self) -> None:
        """Poll and handle all pending device events."""
        events = self._transport.poll()
        for event in events:
            if event.event_type == "heartbeat":
                self._health.record_heartbeat()

            elif event.event_type == "rfid_detected":
                self._handle_rfid_event(event.payload)

            elif event.event_type == "command_result":
                logger.debug("Command result: %s", event.payload.get("status"))

    def _handle_rfid_event(self, payload: dict[str, object]) -> None:
        """Handle an incoming RFID detection event.

        Transitions: IDLE -> CARD_VALIDATING -> VERIFYING or DENIED
        """
        if self._state != SessionState.IDLE:
            logger.debug("RFID event ignored -- session already active")
            return

        uid = str(payload.get("uid", ""))
        if not uid:
            logger.warning("RFID event missing 'uid' field")
            return

        self._state = SessionState.CARD_VALIDATING
        logger.info("RFID detected: %s", uid)

        # Look up card owner
        owner = self._identity_repo.get_card_owner(uid)
        if owner is None:
            logger.info("Unknown or inactive card: %s", uid)
            self._deny_and_reset(uid, ReasonCode.UNKNOWN_RFID)
            return

        # Card is valid -- create verification session
        now = self._clock.now_monotonic()
        self._session = AccessSession(
            session_id=str(uuid.uuid4()),
            card_uid=uid,
            expected_person_id=owner.person_id,
            started_at=now,
            deadline=now + self._config.verification_window_s,
        )
        self._state = SessionState.VERIFYING
        logger.info(
            "Session %s: verifying %s for card %s (deadline=%.1fs)",
            self._session.session_id,
            owner.display_name,
            uid,
            self._config.verification_window_s,
        )

    def _evaluate_frame(self) -> None:
        """Acquire one camera frame, run vision pipeline, evaluate policy."""
        if self._session is None:
            return

        now = self._clock.now_monotonic()

        # Health check
        health = self._health.check()
        if not health.overall_healthy:
            logger.error("System health check failed -- transitioning to FAULT")
            self._state = SessionState.FAULT
            self._deny_and_reset(
                self._session.card_uid, ReasonCode.DEVICE_LINK_ERROR
            )
            return

        # Acquire frame
        frame = self._camera.read()
        if frame is None:
            # Camera failure -- evaluate with no biometric
            biometric: BiometricFrameResult | None = None
        else:
            # Detect faces
            detected_faces: list[DetectedFace] = self._detector.detect(frame)
            face_count = len(detected_faces)

            if face_count == 0:
                biometric = BiometricFrameResult(
                    face_count=0, recognized_person_id=None, distance=float("inf")
                )
            elif face_count > 1 and not self._config.allow_multiple_faces:
                biometric = BiometricFrameResult(
                    face_count=face_count, recognized_person_id=None, distance=float("inf")
                )
            else:
                # Crop the first detected face and recognize
                best_face = detected_faces[0]
                x, y, w, h = best_face.bbox
                # Clamp to frame bounds
                fh, fw = frame.shape[:2]
                x = max(0, x)
                y = max(0, y)
                w = min(w, fw - x)
                h = min(h, fh - y)
                face_crop = frame[y : y + h, x : x + w]

                result = self._recognizer.recognize(
                    face_crop,
                    expected_identity=self._session.expected_person_id,
                )

                biometric = BiometricFrameResult(
                    face_count=1,
                    recognized_person_id=result.identity,
                    distance=result.score
                    if result.model_id == "lbph_recognizer"
                    else (1.0 - result.score),  # Invert cosine for distance semantics
                )

        # Evaluate authorization policy
        threshold = self._config.lbph_threshold
        recognizer_id, _ = self._recognizer.get_model_info()
        if recognizer_id == "sface_recognizer":
            # For SFace, the policy threshold comparison is inverted:
            # we pass (1 - cosine_similarity) as distance, so the threshold
            # must be (1 - sface_threshold)
            threshold = 1.0 - self._config.sface_threshold

        decision = AuthorizationPolicy.evaluate(
            session=self._session,
            biometric=biometric,
            now_monotonic=now,
            threshold=threshold,
            required_matches=self._config.required_consistent_matches,
        )

        # Log audit event
        self._event_logger.log_decision(decision, self._session.card_uid)

        # Act on decision
        if decision.result == DecisionResult.GRANT:
            self._grant_access()
        elif decision.result == DecisionResult.DENY:
            self._deny_and_reset(self._session.card_uid, decision.reason)

        # CONTINUE: keep scanning (do nothing, next tick will evaluate again)

    def _grant_access(self) -> None:
        """Command the door to open and transition to GRANTED."""
        if self._session is None:
            return

        self._state = SessionState.GRANTED
        logger.info("ACCESS GRANTED for session %s", self._session.session_id)

        command = DeviceCommand(
            command_id=str(uuid.uuid4()),
            session_id=self._session.session_id,
            decision="grant",
            reason=ReasonCode.MATCHED_OWNER.value,
            door_hold_ms=int(self._config.door_hold_s * 1000),
        )

        try:
            self._transport.send_access_command(command)
        except ConnectionError:
            logger.error("Failed to send grant command -- link down")
            self._state = SessionState.FAULT

        self._session = None
        self._state = SessionState.IDLE

    def _deny_and_reset(self, card_uid: str, reason: ReasonCode) -> None:
        """Command denial indicators and reset to IDLE."""
        session_id = self._session.session_id if self._session else str(uuid.uuid4())

        self._state = SessionState.DENIED
        logger.info("ACCESS DENIED: %s (card=%s)", reason.value, card_uid)

        command = DeviceCommand(
            command_id=str(uuid.uuid4()),
            session_id=session_id,
            decision="deny",
            reason=reason.value,
            door_hold_ms=0,
        )

        try:
            self._transport.send_access_command(command)
        except ConnectionError:
            logger.error("Failed to send deny command -- link down")

        self._session = None
        self._state = SessionState.IDLE
