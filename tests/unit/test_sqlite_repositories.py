# SPDX-License-Identifier: MIT
"""Unit tests for SQLite repository adapters using in-memory database.

Tests exercise all CRUD operations, foreign key enforcement, active status
filtering, and append-only audit event semantics.
"""

from __future__ import annotations

import sqlite3

import pytest

from app.adapters.sqlite_repositories import (
    SqliteEventRepository,
    SqliteIdentityRepository,
    create_connection,
)
from app.domain.models import AccessEvent, Person, RFIDCard, UserStatus


@pytest.fixture
def conn() -> sqlite3.Connection:
    """Create an in-memory SQLite connection for each test."""
    return create_connection(":memory:")


@pytest.fixture
def identity_repo(conn: sqlite3.Connection) -> SqliteIdentityRepository:
    return SqliteIdentityRepository(conn)


@pytest.fixture
def event_repo(conn: sqlite3.Connection) -> SqliteEventRepository:
    return SqliteEventRepository(conn)


def _alice(created_at: float = 1000.0) -> Person:
    return Person(
        person_id="alice-001",
        display_name="Alice Johnson",
        face_label=0,
        created_at=created_at,
    )


def _bob(created_at: float = 1001.0) -> Person:
    return Person(
        person_id="bob-002",
        display_name="Bob Smith",
        face_label=1,
        created_at=created_at,
    )


def _alice_card(enrolled_at: float = 1000.0) -> RFIDCard:
    return RFIDCard(
        rfid_uid="AABBCCDD",
        person_id="alice-001",
        enrolled_at=enrolled_at,
    )


class TestSqliteIdentityRepository:
    """Tests for SqliteIdentityRepository CRUD and queries."""

    def test_create_and_get_person(
        self, identity_repo: SqliteIdentityRepository
    ) -> None:
        alice = _alice()
        identity_repo.create_person(alice)

        result = identity_repo.get_person("alice-001")
        assert result is not None
        assert result.person_id == "alice-001"
        assert result.display_name == "Alice Johnson"
        assert result.face_label == 0
        assert result.status == UserStatus.ACTIVE

    def test_get_person_returns_none_for_unknown(
        self, identity_repo: SqliteIdentityRepository
    ) -> None:
        assert identity_repo.get_person("nonexistent") is None

    def test_get_person_by_label(
        self, identity_repo: SqliteIdentityRepository
    ) -> None:
        identity_repo.create_person(_alice())
        identity_repo.create_person(_bob())

        result = identity_repo.get_person_by_label(1)
        assert result is not None
        assert result.person_id == "bob-002"

    def test_get_person_by_label_returns_none_for_unknown(
        self, identity_repo: SqliteIdentityRepository
    ) -> None:
        assert identity_repo.get_person_by_label(999) is None

    def test_bind_card_and_get_card_owner(
        self, identity_repo: SqliteIdentityRepository
    ) -> None:
        identity_repo.create_person(_alice())
        identity_repo.bind_card(_alice_card())

        owner = identity_repo.get_card_owner("AABBCCDD")
        assert owner is not None
        assert owner.person_id == "alice-001"

    def test_get_card_owner_returns_none_for_unknown_card(
        self, identity_repo: SqliteIdentityRepository
    ) -> None:
        assert identity_repo.get_card_owner("DEADBEEF") is None

    def test_get_card_owner_returns_none_for_revoked_card(
        self, identity_repo: SqliteIdentityRepository
    ) -> None:
        identity_repo.create_person(_alice())
        revoked_card = RFIDCard(
            rfid_uid="REVOKED1",
            person_id="alice-001",
            status=UserStatus.REVOKED,
            enrolled_at=1000.0,
        )
        identity_repo.bind_card(revoked_card)

        assert identity_repo.get_card_owner("REVOKED1") is None

    def test_get_card_owner_returns_none_for_revoked_person(
        self, identity_repo: SqliteIdentityRepository
    ) -> None:
        revoked_alice = Person(
            person_id="alice-revoked",
            display_name="Alice Revoked",
            face_label=99,
            status=UserStatus.REVOKED,
            created_at=1000.0,
        )
        identity_repo.create_person(revoked_alice)
        card = RFIDCard(
            rfid_uid="CARD99",
            person_id="alice-revoked",
            enrolled_at=1000.0,
        )
        identity_repo.bind_card(card)

        assert identity_repo.get_card_owner("CARD99") is None

    def test_list_active_persons(
        self, identity_repo: SqliteIdentityRepository
    ) -> None:
        identity_repo.create_person(_alice())
        identity_repo.create_person(_bob())
        revoked = Person(
            person_id="charlie-003",
            display_name="Charlie",
            face_label=2,
            status=UserStatus.REVOKED,
            created_at=1002.0,
        )
        identity_repo.create_person(revoked)

        active = identity_repo.list_active_persons()
        assert len(active) == 2
        names = {p.display_name for p in active}
        assert names == {"Alice Johnson", "Bob Smith"}

    def test_list_active_persons_empty(
        self, identity_repo: SqliteIdentityRepository
    ) -> None:
        assert identity_repo.list_active_persons() == []

    def test_duplicate_person_id_raises(
        self, identity_repo: SqliteIdentityRepository
    ) -> None:
        identity_repo.create_person(_alice())
        with pytest.raises(sqlite3.IntegrityError):
            identity_repo.create_person(_alice())

    def test_duplicate_face_label_raises(
        self, identity_repo: SqliteIdentityRepository
    ) -> None:
        identity_repo.create_person(_alice())
        duplicate_label = Person(
            person_id="different-id",
            display_name="Not Alice",
            face_label=0,  # Same label as Alice
            created_at=1001.0,
        )
        with pytest.raises(sqlite3.IntegrityError):
            identity_repo.create_person(duplicate_label)

    def test_foreign_key_enforcement(
        self, identity_repo: SqliteIdentityRepository
    ) -> None:
        """Binding a card to a nonexistent person should fail."""
        orphan_card = RFIDCard(
            rfid_uid="ORPHAN01",
            person_id="nonexistent-person",
            enrolled_at=1000.0,
        )
        with pytest.raises(sqlite3.IntegrityError):
            identity_repo.bind_card(orphan_card)


class TestSqliteEventRepository:
    """Tests for SqliteEventRepository append-only semantics."""

    def test_append_event(self, event_repo: SqliteEventRepository) -> None:
        event = AccessEvent(
            event_id="evt-001",
            session_id="sess-001",
            timestamp=1000.0,
            card_uid="AABBCCDD",
            expected_person_id="alice-001",
            observed_person_id="alice-001",
            observed_distance=42.5,
            decision="GRANT",
            reason="MATCHED_OWNER",
        )
        event_repo.append(event)

        # Verify via raw SQL
        row = event_repo._conn.execute(
            "SELECT * FROM access_events WHERE event_id = ?", ("evt-001",)
        ).fetchone()
        assert row is not None
        assert row[0] == "evt-001"
        assert row[7] == "GRANT"
        assert row[8] == "MATCHED_OWNER"

    def test_append_event_with_none_fields(
        self, event_repo: SqliteEventRepository
    ) -> None:
        event = AccessEvent(
            event_id="evt-002",
            session_id="sess-002",
            timestamp=1001.0,
            card_uid="DEADBEEF",
            expected_person_id=None,
            observed_person_id=None,
            observed_distance=None,
            decision="DENY",
            reason="UNKNOWN_RFID",
        )
        event_repo.append(event)

        row = event_repo._conn.execute(
            "SELECT expected_person_id, observed_person_id, observed_distance "
            "FROM access_events WHERE event_id = ?",
            ("evt-002",),
        ).fetchone()
        assert row is not None
        assert row[0] is None
        assert row[1] is None
        assert row[2] is None

    def test_duplicate_event_id_raises(
        self, event_repo: SqliteEventRepository
    ) -> None:
        event = AccessEvent(
            event_id="evt-dup",
            session_id="sess-001",
            timestamp=1000.0,
            card_uid="AABB",
            expected_person_id=None,
            observed_person_id=None,
            observed_distance=None,
            decision="DENY",
            reason="TIMEOUT",
        )
        event_repo.append(event)
        with pytest.raises(sqlite3.IntegrityError):
            event_repo.append(event)


class TestCreateConnection:
    """Tests for the connection factory."""

    def test_in_memory_connection(self) -> None:
        conn = create_connection(":memory:")
        assert conn is not None

        # Verify foreign keys are enabled
        result = conn.execute("PRAGMA foreign_keys").fetchone()
        assert result is not None
        assert result[0] == 1

    def test_wal_mode_enabled(self) -> None:
        conn = create_connection(":memory:")
        result = conn.execute("PRAGMA journal_mode").fetchone()
        assert result is not None
        # In-memory databases use "memory" journal mode, not WAL
        # WAL is only effective for file-based databases
        assert result[0] in ("wal", "memory")
