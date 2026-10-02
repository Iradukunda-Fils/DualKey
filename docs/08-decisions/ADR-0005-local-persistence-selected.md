# ADR-0005: Local SQLite & Filesystem Persistence Selected

**Document ID:** `ADR-0005`  
**Status:** Accepted  
**Date:** September 29, 2026  
**Deciders:** Lead Software Architect, Systems Engineer, Embedded Engineer  

---

## 1. Context & Problem Statement

DualKey requires persistent storage for user identities (`Person`), card associations (`RFIDCard`), facial sample images (`FaceSample`), audit telemetry (`AccessEvent`), and compiled recognition models (`lbph.yml`). We must choose between:
1. Distributed or client-server databases (PostgreSQL, MySQL, MongoDB).
2. Local key-value stores (Redis, RocksDB).
3. Local embedded SQLite 3 and flat files.

---

## 2. Decision

We select **embedded SQLite 3 (`data/app.db`) for relational metadata and audit events, paired with local filesystem storage for raw images and YAML models**.

---

## 3. Rationale

1. **Zero External Daemon Dependencies:** SQLite runs in-process via Python's standard `sqlite3` library. No separate database server installation, configuration, or network listening port is required.
2. **ACID Transactions:** SQLite provides full ACID compliance with Write-Ahead Logging (`WAL`), ensuring database integrity even during sudden power loss.
3. **Simplicity for MVP:** With 1 door and a small user population, the read/write load is minimal. Relational tables enable foreign key cascading and straightforward SQL auditing.
4. **Offline Sovereignty:** Data never leaves the host machine, guaranteeing privacy and zero internet dependence.

---

## 4. Consequences

### Positive
* Single-file database backup (`cp data/app.db backup.db`).
* In-memory database testing (`:memory:`) executes unit tests in milliseconds.

### Negative / Trade-offs
* Multi-door installations would eventually require a centralized database. However, this is addressed via the `IdentityRepository` interface seam when justified.
