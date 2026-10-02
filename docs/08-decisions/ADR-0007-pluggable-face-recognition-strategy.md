# ADR-0007: Pluggable Open-Source Face Recognition Strategy (LBPH Baseline & Modern SFace/YuNet)

**Document ID:** `ADR-0007`  
**Status:** Accepted  
**Date:** September 29, 2026  
**Deciders:** Lead Software Architect, Systems Engineer, Embedded Engineer, AI Engineer  

---

## 1. Context & Problem Statement

DualKey requires a facial recognition pipeline that fulfills the original educational requirement (OpenCV LBPH) while supporting modern computer-vision capabilities (deep embeddings, landmark alignment, and neural detection) without introducing distributed infrastructure, cloud dependencies, or unverified licensing terms.

We need an architectural strategy that:
1. Keeps OpenCV LBPH as the mandatory, lightweight educational baseline.
2. Integrates modern open-source models (YuNet detector and SFace recognizer from OpenCV Zoo) behind abstract ports.
3. Clarifies that fine-tuning deep neural networks on a tiny enrollment set ($\sim 20$ images for 1–2 individuals) is an anti-pattern, adopting instead embedding extraction with prototype comparison.
4. Complies strictly with permissive open-source licensing (avoiding non-commercial research models such as InsightFace default weights).

---

## 2. Decision

We adopt a **Pluggable Face Recognition Strategy** governed by the following rules:

1. **Mandatory Educational Baseline:**
   * **Haar Cascade Detector** (`haarcascade_frontalface_default.xml`) paired with **OpenCV LBPH Recognizer** (`cv2.face.LBPHFaceRecognizer`) remains fully implemented, tested, and selectable as the baseline backend.
2. **Modern Open-Source Inference Backend:**
   * **YuNet Face Detector** (ONNX, MIT License, OpenCV Zoo) for lightweight, robust detection and 5-point facial landmark alignment.
   * **SFace Recognizer** (ONNX, Apache 2.0 License, OpenCV Zoo) for deep 128-dimensional facial embedding extraction and cosine similarity matching.
3. **No Automatic Fine-Tuning:**
   * The system will **not** fine-tune deep models on small enrollment sets.
   * Instead, it implements the following pattern:
     ```text
     Pretrained Model (YuNet + SFace)
            ↓
     Face Detection & 5-Point Landmark Alignment
            ↓
     128D Embedding Extraction
            ↓
     Enrollment Identity Prototype (Mean Normalized Embedding)
            ↓
     Cosine Similarity Measurement
            ↓
     Calibrated Similarity Threshold Gate
            ↓
     Multi-Frame Consensus (N >= 3)
            ↓
     Authorization Decision
     ```
4. **Licensing Discipline:**
   * Only models with explicit permissive licenses (MIT, Apache 2.0, BSD) are admitted to the repository manifest. Models with non-commercial / research-only restrictions (such as InsightFace pretrained zoo weights) are strictly excluded from the production pipeline.
5. **Decoupled Architecture Ports:**
   * The authorization engine consumes normalized `RecognitionResult` objects and has zero knowledge of which backend is active.

```text
                  DualKey Face Pipeline

                         FaceRecognizerPort
                                │
               ┌────────────────┼────────────────┐
               │                │                │
             LBPH             SFace        Future Model
               │                │                │
           baseline         embeddings      replaceable
          (Chi-square)       (Cosine)            │
               │                │                │
               └────────────────┼────────────────┘
                                ▼
                       RecognitionResult
                                │
                                ▼
                       Authorization Engine
                                │
                       RFID ↔ Face Binding
                                │
                                ▼
                           Servo Command
```

---

## 3. Consequences

### Positive
* Preserves original project requirements while demonstrating modern deep learning engineering.
* Rapid enrollment: computing 20 embeddings and averaging them into an identity prototype takes $< 500\text{ ms}$ on CPU with zero retraining overhead.
* Permissive licensing ensures the prototype can be freely used, demonstrated, and distributed.
* Clear benchmarking utility (`tools/evaluate_face_models.py`) enables evidence-based performance comparison.

### Negative / Trade-offs
* Requires managing ONNX model files and manifest configurations in `models/`.
* Higher CPU utilization during SFace inference compared to classical LBPH (measured and compared empirically in Phase 5/7).
