# Face Recognition & Computer Vision Pipeline

**Document ID:** `DOC-03-VISION`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Detection vs. Recognition Architectural Distinction

A critical engineering principle in DualKey is the separation of **Face Detection** from **Face Recognition**:

```text
+-----------------------+              +-------------------------------------+
|    Face Detection     |              |          Face Recognition           |
|                       |              |                                     |
| "Is there a human     |   ════════>  | "Does this detected face resemble   |
|  face in this frame?" |              |  the enrolled identity of Person X?"|
+-----------------------+              +-------------------------------------+
```

1. **Face Detection:** Discovers spatial bounding boxes $(x, y, w, h)$ containing faces. It does not know or care who the person is.
2. **Face Recognition:** Takes a normalized crop of a detected face, extracts texture patterns, compares histograms against the trained model, and computes statistical distance to enrolled identities.

---

## 2. Supported Pipelines: Baseline & Modern

DualKey supports two selectable vision pipelines behind the abstract `FaceDetectorPort` and `FaceRecognizerPort`:

### 2.1 Pipeline A: Haar + LBPH (Educational Baseline)
```text
[Webcam Frame (640x480)]
            │
            ▼
[Haar Cascade: detectMultiScale()]
            │ Bounding Boxes [(x, y, w, h)]
            ▼
[Quality Gate: Exactly One Face]
            │
            ▼
[Crop & Preprocessing: 100x100 Grayscale + equalizeHist()]
            │
            ▼
[LBPH Classifier: predict()]
            │ (predicted_label: int, chi2_distance: float)
            ▼
[Distance Threshold Check (<= 65.0)]
            │
            ▼
[RecognitionResult: (identity, score, is_match, "lbph")]
```

### 2.2 Pipeline B: YuNet + SFace (Modern Open-Source AI Backend)
```text
[Webcam Frame (640x480 BGR)]
            │
            ▼
[YuNet ONNX Detector (FaceDetectorYN)]
  - Evaluates score >= 0.85
  - Outputs BBox + 5 Facial Landmarks (Right Eye, Left Eye, Nose, Right Mouth, Left Mouth)
            │
            ▼
[Quality Gate: Exactly One Face (BBox Area >= 80x80 px)]
            │
            ▼
[5-Point Affine Landmark Alignment & Crop to 112x112 BGR]
            │
            ▼
[SFace ONNX Recognizer (FaceRecognizerSF)]
  - Extracts 128-dimensional L2-normalized feature vector (Embedding)
            │
            ▼
[Cosine Similarity Matching against Enrolled Identity Prototype]
  - score = dot(test_embedding, prototype_embedding)
  - threshold check: score >= config.sface_threshold (default 0.363)
            │
            ▼
[RecognitionResult: (identity, cosine_similarity, is_match, "sface")]
```

---

## 3. LBPH Parameter Baseline & Mechanics

DualKey employs OpenCV's `cv2.face.LBPHFaceRecognizer_create` parameterized as follows:

| Parameter | Baseline Value | Description & Rationale |
| :--- | :--- | :--- |
| `radius` | `1` | Circular radius of pixel neighborhood around central pixel. |
| `neighbors` | `8` | Number of sample points taken along the circular radius. |
| `grid_x` | `8` | Number of horizontal cells the face crop is partitioned into. |
| `grid_y` | `8` | Number of vertical cells the face crop is partitioned into. |
| `threshold` | `TBD` (Calibrated) | Maximum chi-square distance cutoff. Samples yielding distance above this are rejected. |

### How LBPH Computes Distance
LBPH divides the normalized $100 \times 100$ image into an $8 \times 8$ grid of cells (64 total cells). Within each cell, local binary pattern histograms are generated and concatenated into a global histogram. The classifier compares the test histogram against enrolled histograms using the **Chi-Square Distance**:

$$\chi^2(H_{\text{test}}, H_{\text{model}}) = \sum_{i} \frac{(H_{\text{test}}[i] - H_{\text{model}}[i])^2}{H_{\text{test}}[i] + H_{\text{model}}[i]}$$

* **Distance $\approx 0$:** Identical image (perfect match).
* **Distance $30 - 65$:** Typical matching range under consistent ambient lighting.
* **Distance $> 75$:** Substantial variance; represents unknown face or noise.

---

## 4. SFace & YuNet Technical Specification

### 4.1 YuNet Face Detector (`FaceDetectorYN`)
* **Source:** OpenCV Zoo (`face_detection_yunet_2023mar.onnx`), MIT License.
* **Architecture:** Ultra-lightweight CNN designed specifically for real-time edge CPU face detection.
* **Output Vector:** 15 elements: `[x, y, w, h, x_re, y_re, x_le, y_le, x_nt, y_nt, x_rc, y_rc, x_lc, y_lc, score]`.

### 4.2 Facial Alignment & Preprocessing
Using the 5 facial landmark coordinates provided by YuNet:
1. Compute similarity transformation matrix mapping landmarks to canonical 5-point coordinates in a $112 \times 112$ bounding space.
2. Apply `cv2.warpAffine` to produce a pose-normalized, upright facial crop.

### 4.3 SFace Feature Extraction & Prototype Matching (`FaceRecognizerSF`)
* **Source:** OpenCV Zoo (`face_recognition_sface_2021dec.onnx`), Apache 2.0 License.
* **Output:** 128-dimensional floating-point embedding vector, L2-normalized ($\|\mathbf{e}\|_2 = 1$).
* **Enrollment Prototype Construction:** For a newly enrolled user with $M$ valid samples, compute the prototype as the normalized mean vector:
  $$\mathbf{p}_{\text{person}} = \frac{\sum_{i=1}^M \mathbf{e}_i}{\left\| \sum_{i=1}^M \mathbf{e}_i \right\|_2}$$
* **Similarity Computation:** Cosine similarity is computed directly via the dot product:
  $$S(\mathbf{e}_{\text{test}}, \mathbf{p}_{\text{expected}}) = \mathbf{e}_{\text{test}} \cdot \mathbf{p}_{\text{expected}}$$
* **Match Invariant:** Access match requires $S \ge \theta_{\text{cosine}}$ (default $\theta_{\text{cosine}} = 0.363$).

---

## 5. Empirical Threshold Calibration Protocol

> [!WARNING]
> **No Hardcoded Universal Threshold:** There is no universally secure threshold. Changing the active model or environment must trigger recalibration.

### Calibration Procedure
1. Perform enrollment for Person A and Person B under operational room lighting.
2. Run diagnostic tool `python tools/evaluate_face_models.py --calibrate`.
3. Capture 50 true-positive frames of Person A $\to$ record score distribution ($\mu_{\text{TP}}, \sigma_{\text{TP}}$).
4. Capture 50 true-negative frames of Person B posing as Person A $\to$ record false-positive score distribution.
5. Calibrate threshold:
   - For LBPH (distance metric): $\theta = \min(d_{\text{FP}}) - 10.0$ or $\mu_{\text{TP}} + 2\sigma_{\text{TP}}$.
   - For SFace (similarity metric): $\theta = \max(S_{\text{FP}}) + 0.05$ or $\mu_{\text{TP}} - 2\sigma_{\text{TP}}$.
6. Record calibrated values in `models/registry.json`.
