# Verification Strategy & Test Pyramid

**Document ID:** `DOC-06-STRATEGY`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Test Pyramid Architecture

DualKey enforces a structured test pyramid ensuring that the majority of test scenarios execute rapidly in pure virtualized environments without requiring physical hardware.

```text
                  /\
                 /  \      Hardware-in-the-Loop (HIL) Tests
                / HIL\     - Real ESP32, cards, servo, LEDs, buzzer, camera
               /------\    - Tests ACC-001..ACC-010 under controlled conditions
              /        \
             /  INTEGR. \  Integration Tests
            /  HARNESS   \ - Simulated Serial Device, In-Memory SQLite, Mock Camera
           /--------------\ - Full AccessController tick execution
          /                \
         /   UNIT TESTING   \ Unit Tests (Pure Domain & Protocols)
        /     (90%+ COVER)   \- AuthorizationPolicy, State Transitions, NDJSON framing
       /----------------------\ - Executes in < 2 seconds via pytest
```

---

## 2. Test Level Definitions & Gates

| Test Level | Scope & Target Modules | Execution Environment | Gating Standard |
| :--- | :--- | :--- | :--- |
| **Unit Testing** | `app/domain/`, `app/application/`, protocol serializers. | Pure Python virtual environment via `pytest`. | **$\ge 90\%$ statement coverage** across domain and application layers. Zero hardware required. |
| **Integration Testing**| `AccessController` wired to `MockCameraAdapter`, `SimulatedSerialAdapter`, and SQLite. | Local automated test suite. | Validates complete session lifecycles, timeout expiration, and error handling. |
| **Hardware-in-Loop (HIL)**| Physical ESP32, MFRC522, SG90 servo, LEDs, buzzer, laptop webcam. | Physical breadboard setup. | All 10 acceptance scenarios (`ACC-001` through `ACC-010`) verified manually with evidence logs. |
| **Failure Injection** | Physical cable disconnects, camera occlusion, malformed JSON injection. | Physical & simulated environments. | $100\%$ fail-closed confirmation. Actuator never releases unexpectedly. |
| **Model Evaluation** | `tools/evaluate_face_models.py` benchmarking LBPH vs YuNet+SFace. | Real laptop webcam & enrolled sample sets. | Empirical measurement of latency, FAR, FRR, pose/light sensitivity. |

---

## 3. Evidence-Based Model Evaluation Protocol

To prevent subjective model selection, `tools/evaluate_face_models.py` executes empirical benchmarks on the local workstation hardware measuring:
1. **Inference Latency:** Detection latency (ms) and recognition latency (ms) averaged over 100 frames.
2. **False Acceptance & False Rejection:** Tested against distinct enrolled and un-enrolled subjects.
3. **Lighting & Pose Sensitivity:** Evaluated under high lux, dim lux, frontal, and $15^\circ$ angled poses.
4. **Hardware Footprint:** CPU utilization percentage and memory (RSS) delta.

Results are documented in `docs/06-testing/model-evaluation.md` and used to calibrate model thresholds.
