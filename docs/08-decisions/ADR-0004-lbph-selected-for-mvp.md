# ADR-0004: OpenCV LBPH Algorithm Selected for MVP Biometrics

**Document ID:** `ADR-0004`  
**Status:** Accepted  
**Date:** September 29, 2026  
**Deciders:** Lead Software Architect, Systems Engineer, Embedded Engineer  

---

## 1. Context & Problem Statement

DualKey requires a facial recognition algorithm suitable for an educational two-factor access control prototype. Options considered include:
1. Deep learning embeddings (FaceNet, InsightFace, ArcFace via PyTorch/ONNX).
2. Cloud biometric APIs (AWS Rekognition, Azure Face API).
3. Classical texture/eigen methods in OpenCV (Eigenfaces, Fisherfaces, LBPH).

---

## 2. Decision

We select **OpenCV's Local Binary Patterns Histograms (LBPH)** recognizer (`cv2.face.LBPHFaceRecognizer`) as the normative biometric model for the MVP.

---

## 3. Rationale

1. **Lightweight & Fully Offline:** LBPH requires zero GPU acceleration, runs deterministically on standard commodity laptop CPUs, and requires zero external network calls.
2. **Minimal Sample Requirement:** Unlike deep neural networks that require extensive data or heavy pre-trained weights ($100\text{ MB} - 1\text{ GB}$), LBPH trains effectively from as few as $15 - 20$ local crops in $< 1\text{ second}$.
3. **Transparent Mathematical Model:** LBPH computes straightforward chi-square histogram distances, making threshold calibration and decision logic easy to inspect, test, and understand for educational purposes.
4. **Architectural Seam:** By isolating LBPH behind `FaceRecognizerPort`, modern neural models can be integrated later without altering the domain policy.

---

## 4. Consequences & Limitations

### Positive
* Zero cloud dependencies, zero external licensing costs, instant local training.
* Completely reproducible and testable in local unit/integration tests.

### Negative / Known Limitation
* **Vulnerable to 2D presentation attacks:** A printed color photo or tablet screen can reproduce local texture gradients and fool the recognizer. This is accepted and explicitly documented in `DOC-05-LIMIT`.
