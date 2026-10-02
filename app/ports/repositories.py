# SPDX-License-Identifier: MIT
"""Repository ports — abstract interfaces for identity and audit persistence.

Reference: DOC-04-PORTS S2.4-2.5 (docs/04-interfaces/internal-interfaces.md)
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.domain.models import AccessEvent, Person, RFIDCard


@runtime_checkable
class IdentityRepository(Protocol):
    """Structural interface for identity data access.

    Provides CRUD operations for persons and RFID card bindings.
    Implementations may use SQLite, in-memory dictionaries, or any
    other storage backend.
    """

    def get_card_owner(self, uid: str) -> Person | None:
        """Retrieve the Person owning the specified active card UID.

        Args:
            uid: Hex-encoded RFID card UID.

        Returns:
            The owning Person if the card is active, or None.
        """
        ...

    def get_person(self, person_id: str) -> Person | None:
        """Retrieve a Person by their unique identifier.

        Args:
            person_id: UUIDv4 person identifier.

        Returns:
            The Person if found, or None.
        """
        ...

    def get_person_by_label(self, face_label: int) -> Person | None:
        """Retrieve a Person corresponding to an OpenCV integer label.

        Used by LBPH recognizer to map predicted label → person identity.

        Args:
            face_label: The integer label assigned during enrollment.

        Returns:
            The Person if found, or None.
        """
        ...

    def create_person(self, person: Person) -> None:
        """Persist a new Person record.

        Args:
            person: The Person entity to store.

        Raises:
            ValueError: If person_id or face_label already exists.
        """
        ...

    def bind_card(self, card: RFIDCard) -> None:
        """Bind an RFID card to a person.

        Args:
            card: The RFIDCard entity to store.

        Raises:
            ValueError: If rfid_uid already exists.
        """
        ...

    def list_active_persons(self) -> list[Person]:
        """List all persons with ACTIVE status.

        Returns:
            A list of active Person entities.
        """
        ...


@runtime_checkable
class EventRepository(Protocol):
    """Structural interface for immutable audit event storage.

    Access events are append-only and must never be modified or deleted.
    """

    def append(self, event: AccessEvent) -> None:
        """Append an immutable audit event to persistent storage.

        Args:
            event: The AccessEvent to persist.
        """
        ...
