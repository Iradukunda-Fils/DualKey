# Architecture Overview & Principles

**Document ID:** `DOC-02-OVERVIEW`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Architectural Philosophy

DualKey is engineered around the principle of **architectural honesty and boundary scalability**. Rather than prematurely deploying distributed infrastructure (brokers, cloud APIs, microservices, container orchestrators) for an educational single-door prototype, the system is structured as a clean, modular monolith utilizing **Hexagonal Architecture (Ports & Adapters)**.

This ensures:
1. The entire access control business policy is testable in milliseconds on a developer workstation with zero hardware attached.
2. Every hardware driver and machine-learning algorithm is isolated behind strict interfaces.
3. Upgrading any individual technology (e.g., migrating from LBPH to deep learning, or from Serial to TLS over TCP) is a plug-in operation that requires zero changes to the core authorization rules.

```text
+-----------------------------------------------------------------------+
|                           APPLICATION DOMAIN                          |
|                                                                       |
|   +---------------------------------------------------------------+   |
|   |                      AuthorizationPolicy                      |   |
|   |  - Pure, deterministic boolean logic                          |   |
|   |  - Enforces 2-factor binding, thresholds, and stable matches   |   |
|   +-------------------------------+-------------------------------+   |
|                                   │                                   |
|   +-------------------------------▼-------------------------------+   |
|   |                       AccessController                        |   |
|   |  - Session lifecycle & 10.0s monotonic deadline management    |   |
|   |  - Coordinates events, vision results, and actuator commands  |   |
|   +-------------------------------+-------------------------------+   |
+-----------------------------------|-----------------------------------+
                                    │
                                    ▼ (Ports / Interfaces)
+-----------------------------------------------------------------------+
|                           PORTS & ADAPTERS                            |
|                                                                       |
|   [CameraPort]          [FaceRecognizerPort]    [DeviceTransportPort] |
|        │                         │                       │            |
|   OpenCVCameraAdapter    OpenCVLBPHAdapter       Esp32SerialAdapter   |
|        │                         │                       │            |
|   Webcam UVC             YAML Model File         USB Serial (NDJSON)  |
+-----------------------------------------------------------------------+
                                                           │
                                                           ▼ (Hardware)
                                                +---------------------+
                                                |   ESP32 Controller  |
                                                |  - MFRC522 SPI RFID |
                                                |  - SG90 Servo PWM   |
                                                |  - LEDs & Buzzer    |
                                                +---------------------+
```

---

## 2. Core Architectural Principles

| Principle | Architectural Decision | Engineering Rationale |
| :--- | :--- | :--- |
| **Single Decision Authority** | `AccessController` + `AuthorizationPolicy` exclusively decide access. | Prevents peripheral handlers, device drivers, or ML components from unilaterally actuating the lock. |
| **Local-First Simplicity** | SQLite 3, local filesystem model files, point-to-point USB CDC serial. | Matches real operational needs: 1 door, 1 host, small user base, zero internet or cloud dependencies. |
| **Ports and Adapters** | `CameraPort`, `FaceRecognizerPort`, `DeviceTransportPort`, `IdentityRepository`. | Keeps domain rules pristine and enables clean unit testing via mocks and simulators. |
| **Fail-Closed by Design** | Safe defaults across host state machines and ESP32 firmware watchdog loops. | Physical access control must never fail open due to software uncertainty, packet loss, or unhandled exceptions. |
| **Explicit State Machine** | Formal session states (`IDLE`, `VERIFYING`, `GRANTED`, `DENIED`, `FAULT`). | Eliminates hidden or competing boolean flags; makes timing, failure paths, and testing fully deterministic. |
| **Scalability by Seam** | Abstractions at transport, persistence, and vision boundaries. | Future scaling is an implementation of an existing port, not a ground-up rewrite of business logic. |

---

## 3. Explicit Non-Optimization Rule

> **"Do not optimize for people or scale that are not here today."**

DualKey intentionally rejects:
* Cloud identity federation (OAuth2/OIDC, Okta, Azure AD)
* Distributed event queues (Apache Kafka, RabbitMQ)
* In-memory key-value caches (Redis, Memcached)
* Container orchestration (Kubernetes, Nomad, Swarm)
* Microservices architecture and service meshes (Envoy, Istio)

Capacity for future growth is provided by **stable architectural contracts and interface boundaries**, not by dead infrastructure.
