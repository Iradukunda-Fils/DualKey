# SPDX-License-Identifier: MIT
"""SQLite repository adapters for identity and audit persistence.

Implements IdentityRepository and EventRepository ports using SQLite 3
with WAL journal mode and foreign key enforcement. Designed for local-first
single-door operation with ACID guarantees.

Reference: DOC-03-PERSIST (docs/03-design/persistence.md)
"""

from __future__ import annotations

import sqlite3
from typing import Final

from app.domain.models import AccessEvent, Person, RFIDCard, UserStatus

_SCHEMA_SQL: Final[str] = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS persons (
    person_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    face_label INTEGER UNIQUE NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS rfid_cards (
    rfid_uid TEXT PRIMARY KEY,
    person_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    enrolled_at REAL NOT NULL,
    FOREIGN KEY(person_id) REFERENCES persons(person_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS face_samples (
    sample_id TEXT PRIMARY KEY,
    person_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    captured_at REAL NOT NULL,
    FOREIGN KEY(person_id) REFERENCES persons(person_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS access_events (
    event_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    timestamp REAL NOT NULL,
    card_uid TEXT NOT NULL,
    expected_person_id TEXT,
    observed_person_id TEXT,
    observed_distance REAL,
    decision TEXT NOT NULL,
    reason TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rfid_cards_person
    ON rfid_cards(person_id);
CREATE INDEX IF NOT EXISTS idx_face_samples_person
    ON face_samples(person_id);
CREATE INDEX IF NOT EXISTS idx_access_events_timestamp
    ON access_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_access_events_session
    ON access_events(session_id);
"""


class SqliteIdentityRepository:
    """SQLite-backed identity repository.

    Manages persons and RFID card bindings with ACID guarantees.
    Uses parameterized queries exclusively to prevent SQL injection.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._conn = connection
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create tables and indexes if they do not exist."""
        self._conn.executescript(_SCHEMA_SQL)

    def get_card_owner(self, uid: str) -> Person | None:
        """Retrieve the active Person owning the specified card UID."""
        row = self._conn.execute(
            """
            SELECT p.person_id, p.display_name, p.face_label,
                   p.status, p.created_at
            FROM rfid_cards c
            JOIN persons p ON c.person_id = p.person_id
            WHERE c.rfid_uid = ?
              AND c.status = 'ACTIVE'
              AND p.status = 'ACTIVE'
            """,
            (uid,),
        ).fetchone()

        if row is None:
            return None
        return self._row_to_person(row)

    def get_person(self, person_id: str) -> Person | None:
        """Retrieve a Person by their unique identifier."""
        row = self._conn.execute(
            "SELECT person_id, display_name, face_label, status, created_at "
            "FROM persons WHERE person_id = ?",
            (person_id,),
        ).fetchone()

        if row is None:
            return None
        return self._row_to_person(row)

    def get_person_by_label(self, face_label: int) -> Person | None:
        """Retrieve a Person corresponding to an OpenCV integer label."""
        row = self._conn.execute(
            "SELECT person_id, display_name, face_label, status, created_at "
            "FROM persons WHERE face_label = ?",
            (face_label,),
        ).fetchone()

        if row is None:
            return None
        return self._row_to_person(row)

    def create_person(self, person: Person) -> None:
        """Persist a new Person record."""
        self._conn.execute(
            "INSERT INTO persons (person_id, display_name, face_label, "
            "status, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                person.person_id,
                person.display_name,
                person.face_label,
                person.status.value,
                person.created_at,
            ),
        )
        self._conn.commit()

    def bind_card(self, card: RFIDCard) -> None:
        """Bind an RFID card to a person."""
        self._conn.execute(
            "INSERT INTO rfid_cards (rfid_uid, person_id, status, enrolled_at) "
            "VALUES (?, ?, ?, ?)",
            (
                card.rfid_uid,
                card.person_id,
                card.status.value,
                card.enrolled_at,
            ),
        )
        self._conn.commit()

    def list_active_persons(self) -> list[Person]:
        """List all persons with ACTIVE status."""
        rows = self._conn.execute(
            "SELECT person_id, display_name, face_label, status, created_at "
            "FROM persons WHERE status = 'ACTIVE' ORDER BY display_name",
        ).fetchall()

        return [self._row_to_person(row) for row in rows]

    @staticmethod
    def _row_to_person(row: tuple[str, str, int, str, float]) -> Person:
        """Map a database row tuple to a Person domain entity."""
        return Person(
            person_id=row[0],
            display_name=row[1],
            face_label=row[2],
            status=UserStatus(row[3]),
            created_at=row[4],
        )


class SqliteEventRepository:
    """SQLite-backed audit event repository.

    Append-only: events are never modified or deleted. Each event
    represents an immutable audit record of a single authorization evaluation.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._conn = connection
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create the access_events table if it does not exist."""
        self._conn.executescript(_SCHEMA_SQL)

    def append(self, event: AccessEvent) -> None:
        """Append an immutable audit event to persistent storage."""
        self._conn.execute(
            "INSERT INTO access_events "
            "(event_id, session_id, timestamp, card_uid, "
            "expected_person_id, observed_person_id, observed_distance, "
            "decision, reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                event.event_id,
                event.session_id,
                event.timestamp,
                event.card_uid,
                event.expected_person_id,
                event.observed_person_id,
                event.observed_distance,
                event.decision,
                event.reason,
            ),
        )
        self._conn.commit()


def create_connection(db_path: str) -> sqlite3.Connection:
    """Create a configured SQLite connection with WAL and foreign keys.

    Args:
        db_path: Filesystem path for the database file, or ":memory:"
                 for in-memory testing.

    Returns:
        A configured sqlite3.Connection with WAL mode and foreign keys ON.
    """
    conn = sqlite3.Connection(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn
