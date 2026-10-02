# Model Evaluation Report

> DOC-06-MODEL-EVAL | Phase 12 Validation

## 1. Evaluation Environment

| Parameter | Value |
|-----------|-------|
| Python | 3.12.11 |
| OpenCV | 5.0.0 (opencv-contrib-python) |
| NumPy | 2.5.3 |
| ONNX Runtime | 1.30.0 |
| OS | Arch Linux (kernel TBD) |
| CPU | TBD (run `lscpu`) |
| RAM | TBD |
| Camera | Laptop webcam (USB UVC) |
| Resolution | 640x480 (default) |
| Measurement frames | 100 |
| Warmup frames | 10 |

## 2. Approved Model Configurations

| ID | Detector | Recognizer | License | Threshold |
|----|----------|------------|---------|-----------|
| `haar_lbph` | Haar frontalface | LBPH | BSD (OpenCV) | chi-sq <= 65.0 |
| `yunet_lbph` | YuNet 2023mar | LBPH | MIT (OpenCV Zoo) | chi-sq <= 65.0 |
| `yunet_sface` | YuNet 2023mar | SFace 2021dec | Apache 2.0 (OpenCV Zoo) | cosine >= 0.363 |

## 3. Benchmark Results

### 3.1 Startup Latency

| Backend | Detector Init (ms) | Recognizer Init (ms) | Total (ms) |
|---------|--------------------|-----------------------|------------|
| `haar_lbph` | PENDING | PENDING | PENDING |
| `yunet_lbph` | PENDING | PENDING | PENDING |
| `yunet_sface` | PENDING | PENDING | PENDING |

### 3.2 Per-Frame Latency

| Backend | Detection Mean | Det P95 | Recognition Mean | Rec P95 | E2E Mean | E2E P95 |
|---------|---------------|---------|-----------------|---------|----------|---------|
| `haar_lbph` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| `yunet_lbph` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |
| `yunet_sface` | PENDING | PENDING | PENDING | PENDING | PENDING | PENDING |

### 3.3 Resource Usage

| Backend | CPU Utilization (%) | Peak RSS (MB) |
|---------|--------------------:|-------------:|
| `haar_lbph` | PENDING | PENDING |
| `yunet_lbph` | PENDING | PENDING |
| `yunet_sface` | PENDING | PENDING |

### 3.4 Detection Statistics

| Backend | Total Frames | With Face | No Face | Multi-Face | Detection Rate (%) |
|---------|-------------|-----------|---------|------------|-------------------|
| `haar_lbph` | PENDING | PENDING | PENDING | PENDING | PENDING |
| `yunet_lbph` | PENDING | PENDING | PENDING | PENDING | PENDING |
| `yunet_sface` | PENDING | PENDING | PENDING | PENDING | PENDING |

### 3.5 Recognition Stability

| Backend | Attempts | Matches | Match Rate (%) | Max Consecutive |
|---------|---------|---------|---------------|----------------|
| `haar_lbph` | PENDING | PENDING | PENDING | PENDING |
| `yunet_lbph` | PENDING | PENDING | PENDING | PENDING |
| `yunet_sface` | PENDING | PENDING | PENDING | PENDING |

## 4. Threshold Calibration

### 4.1 LBPH Chi-Square Threshold

The LBPH recognizer uses chi-square distance where LOWER = better match.

| Condition | Expected Range | Documented Threshold |
|-----------|---------------|---------------------|
| Same person, good lighting | 20 - 50 | <= 65.0 |
| Same person, dim lighting | 40 - 80 | <= 65.0 |
| Different person | > 80 | > 65.0 (reject) |

Selected operational threshold: **65.0** (DOC-04-MODEL-MANIFEST)

### 4.2 SFace Cosine Threshold

The SFace recognizer uses cosine similarity where HIGHER = better match.

| Condition | Expected Range | Documented Threshold |
|-----------|---------------|---------------------|
| Same person, good lighting | 0.5 - 0.9 | >= 0.363 |
| Same person, dim lighting | 0.3 - 0.6 | >= 0.363 |
| Different person | < 0.2 | < 0.363 (reject) |

Selected operational threshold: **0.363** (OpenCV Zoo default)

> [!IMPORTANT]
> LBPH threshold and SFace threshold are NOT interchangeable.
> Each model+version+preprocessing+threshold is treated as one configuration.

## 5. Sensitivity Observations

### 5.1 Lighting

| Condition | Haar Detection | YuNet Detection | LBPH Match | SFace Match |
|-----------|---------------|----------------|------------|-------------|
| Normal indoor | PENDING | PENDING | PENDING | PENDING |
| Dim ambient | PENDING | PENDING | PENDING | PENDING |
| Backlit | PENDING | PENDING | PENDING | PENDING |
| Side-lit | PENDING | PENDING | PENDING | PENDING |

### 5.2 Distance

| Distance | Haar Detection | YuNet Detection | LBPH Match | SFace Match |
|----------|---------------|----------------|------------|-------------|
| ~0.5m | PENDING | PENDING | PENDING | PENDING |
| ~1.0m | PENDING | PENDING | PENDING | PENDING |
| ~1.5m | PENDING | PENDING | PENDING | PENDING |
| ~2.0m | PENDING | PENDING | PENDING | PENDING |

### 5.3 Pose

| Pose | Haar Detection | YuNet Detection | LBPH Match | SFace Match |
|------|---------------|----------------|------------|-------------|
| Frontal | PENDING | PENDING | PENDING | PENDING |
| Slight left | PENDING | PENDING | PENDING | PENDING |
| Slight right | PENDING | PENDING | PENDING | PENDING |
| Slight up | PENDING | PENDING | PENDING | PENDING |
| Slight down | PENDING | PENDING | PENDING | PENDING |

## 6. How to Run

```bash
# Evaluate Haar + LBPH baseline (no model downloads needed)
.venv/bin/python tools/evaluate_face_models.py --backend haar_lbph --frames 100

# Evaluate all available backends
.venv/bin/python tools/evaluate_face_models.py --all --frames 100

# Results are written to data/evaluation/
ls data/evaluation/
```

## 7. Notes

- All measurements are hardware-dependent and must be re-run on the target deployment machine.
- The evaluation tool does NOT invent benchmark numbers -- it measures them.
- PENDING values must be filled by running `tools/evaluate_face_models.py` with a live camera.
- Raw latency data is saved as CSV for further analysis.
