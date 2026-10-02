# SPDX-License-Identifier: MIT
"""Structured audit event logger.

Builds immutable AccessEvent records from session state and policy
decisions, then persists them via the EventRepository port.

Reference: DOC-03-LLD (docs/03-design/low-level-design.md)
"""

from __future__ import annotations

import logging
import time
import uuid

from app.domain.decisions import AccessDecision
from app.domain.models import AccessEvent
from app.ports.repositories import EventRepository

logger = logging.getLogger(__name__)


class EventLogger:
    """Builds and persists audit records for every authorization evaluation."""

    def __init__(self, event_repo: EventRepository) -> None:
        self._repo = event_repo

    def log_decision(self, decision: AccessDecision, card_uid: str) -> AccessEvent:
        """Create and persist an audit event from a policy decision.

        Args:
            decision: The authorization policy evaluation result.
            card_uid: The RFID UID that initiated the session.

        Returns:
            The persisted AccessEvent record.
        """
        event = AccessEvent(
            event_id=str(uuid.uuid4()),
            session_id=decision.session_id,
            timestamp=time.time(),
            card_uid=card_uid,
            expected_person_id=decision.expected_person_id,
            observed_person_id=decision.observed_person_id,
            observed_distance=decision.distance,
            decision=decision.result.value.upper(),
            reason=decision.reason.value,
        )
        self._repo.append(event)
        logger.debug(
            "Audit event %s: %s (%s)", event.event_id, event.decision, event.reason
        )
        return event
