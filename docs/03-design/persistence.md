# Persistence Architecture & Database Schema

**Document ID:** `DOC-03-PERSIST`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Storage Strategy Overview

DualKey uses a hybrid persistence strategy optimized for local-first embedded operation:
1. **Relational Metadata & Audit Logs:** Stored in an embedded SQLite 3 database (`data/app.db`).
2. **Raw Biometric Samples:** Stored as normalized PNG files in the local filesystem (`data/faces/<person_id>/`).
3. **Compiled Recognizer Model:** Serialized as an OpenCV YAML/XML file (`data/models/lbph.yml`).

---

## 2. Relational Database Schema (`data/app.db`)

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- 1. Enrolled Person Entities
CREATE TABLE IF NOT EXISTS persons (
    person_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    face_label INTEGER UNIQUE NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at REAL NOT NULL
);

-- 2. Bound RFID Tokens
CREATE TABLE IF NOT EXISTS rfid_cards (
    rfid_uid TEXT PRIMARY KEY,
    person_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    enrolled_at REAL NOT NULL,
    FOREIGN KEY(person_id) REFERENCES persons(person_id) ON DELETE CASCADE
);

-- 3. Archived Face Samples
CREATE TABLE IF NOT EXISTS face_samples (
    sample_id TEXT PRIMARY KEY,
    person_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    captured_at REAL NOT NULL,
    FOREIGN KEY(person_id) REFERENCES persons(person_id) ON DELETE CASCADE
);

-- 4. Immutable Audit Event Log
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

-- 5. Performance Indexes
CREATE INDEX IF NOT EXISTS idx_rfid_cards_person ON rfid_cards(person_id);
CREATE INDEX IF NOT EXISTS idx_face_samples_person ON face_samples(person_id);
CREATE INDEX IF NOT EXISTS idx_access_events_timestamp ON access_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_access_events_session ON access_events(session_id);
```

---

## 3. Atomic Model & Database Consistency

Whenever an enrollment or deletion occurs:
1. **Transaction Begin:** Database opens an atomic transaction.
2. **Filesystem Updates:** New face samples are saved to disk.
3. **Model Re-training:** `LBPHFaceRecognizer.train()` is executed over all active samples.
4. **Atomic Model Write:** The trained model is written to a temporary file (`data/models/lbph.yml.tmp`) and atomically renamed via `os.replace()` to `data/models/lbph.yml`.
5. **Database Commit:** Database record is committed.
6. **Rollback Safety:** If any step fails (e.g. disk full, training error), the database transaction is rolled back and newly written PNG samples are unlinked, guaranteeing that `app.db` and `lbph.yml` are never out of sync.
