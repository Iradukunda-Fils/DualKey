# ADR-0006: NDJSON Over USB Serial Protocol Selected

**Document ID:** `ADR-0006`  
**Status:** Accepted  
**Date:** September 29, 2026  
**Deciders:** Lead Software Architect, Systems Engineer, Embedded Engineer  

---

## 1. Context & Problem Statement

DualKey requires a serialization and framing protocol for host-device communication over a point-to-point USB serial link. Options evaluated:
1. Binary framing protocols (COBS, SLIP with custom binary structs or Protocol Buffers).
2. Character-delimited ASCII strings (e.g., `CARD:A1B2C3D4\n`, `CMD:OPEN\n`).
3. Newline-Delimited JSON (NDJSON).

---

## 2. Decision

We select **Newline-Delimited JSON (NDJSON)** over USB CDC serial ($115200\text{ baud}$, 8N1).

---

## 3. Rationale

1. **Human Readability & Debuggability:** Messages can be observed and debugged directly using standard terminal tools (`picocom`, `minicom`, `screen`) or PlatformIO Serial Monitor without dedicated packet disassemblers.
2. **Extensibility & Schema Evolution:** JSON allows adding fields (e.g. diagnostic uptime, free heap, error codes) without breaking backward compatibility. Top-level `"v": 1` versioning ensures future breaking changes can be gracefully managed.
3. **Maturity of Tooling:** Both Python (`json` standard library) and embedded C++ (`bblanchon/ArduinoJson`) have robust, battle-tested parsers that detect corrupted frames without crashing.
4. **Clean Framing Boundary:** Using ASCII LF (`\n`) as a delimiter provides trivial frame synchronization with zero byte-stuffing complexity.

---

## 4. Consequences

### Positive
* Fast, transparent troubleshooting.
* Correlation IDs (`event_id`, `session_id`, `command_id`) are cleanly represented.

### Negative / Trade-offs
* Text encoding incurs slightly higher byte overhead than compact binary structs (an average NDJSON frame is $\approx 100 - 150\text{ bytes}$). At $115200\text{ baud}$ ($\approx 11.5\text{ KB/s}$), transmitting $150\text{ bytes}$ takes $\approx 13\text{ ms}$, which is well within our $100\text{ ms}$ latency budget.
