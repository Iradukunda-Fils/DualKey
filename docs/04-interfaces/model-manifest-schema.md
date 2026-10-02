# Model Manifest Schema & License Governance Contract

**Document ID:** `DOC-04-MODEL-MANIFEST`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Model Registry Manifest Overview

To prevent scattered model paths and untracked binaries in the repository, DualKey governs all biometric models through a centralized manifest located at:

```text
models/registry.json
```

The manifest identifies exact versions, SHA-256 cryptographic checksums, preprocessing requirements, operational thresholds, and legal licensing terms.

---

## 2. Manifest JSON Schema Specification

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "DualKeyModelRegistry",
  "type": "object",
  "properties": {
    "active_detector": { "type": "string" },
    "active_recognizer": { "type": "string" },
    "detectors": {
      "type": "array",
      "items": { "$ref": "#/$defs/ModelEntry" }
    },
    "recognizers": {
      "type": "array",
      "items": { "$ref": "#/$defs/ModelEntry" }
    }
  },
  "$defs": {
    "ModelEntry": {
      "type": "object",
      "required": [
        "model_id",
        "model_version",
        "model_format",
        "input_size",
        "preprocessing_version",
        "threshold",
        "checksum_sha256",
        "license",
        "license_url",
        "source",
        "restrictions",
        "enabled",
        "artifact_path"
      ],
      "properties": {
        "model_id": { "type": "string" },
        "model_version": { "type": "string" },
        "model_format": { "type": "string", "enum": ["xml", "yml", "onnx"] },
        "input_size": { "type": "array", "items": { "type": "integer" } },
        "preprocessing_version": { "type": "string" },
        "threshold": { "type": "number" },
        "checksum_sha256": { "type": "string" },
        "license": { "type": "string" },
        "license_url": { "type": "string" },
        "source": { "type": "string" },
        "restrictions": { "type": "string" },
        "enabled": { "type": "boolean" },
        "artifact_path": { "type": "string" }
      }
    }
  }
}
```

---

## 3. Approved Model Baseline in Manifest

### 3.1 Baseline Detectors
1. **Haar Cascade (`haar_frontalface`)**
   * **License:** BSD 3-Clause (OpenCV Project).
   * **Format:** XML (`haarcascade_frontalface_default.xml`).
   * **Input:** Grayscale arbitrary resolution.
   * **Intended Use:** Lightweight CPU detection baseline.
2. **YuNet (`yunet_face_detection`)**
   * **License:** MIT License (OpenCV Zoo).
   * **Format:** ONNX (`face_detection_yunet_2023mar.onnx`).
   * **Input:** $320 \times 320$ or $640 \times 640$ BGR.
   * **Intended Use:** Fast DNN detection + 5-point facial landmark output.

### 3.2 Baseline Recognizers
1. **LBPH (`lbph_recognizer`)**
   * **License:** BSD 3-Clause (OpenCV Project).
   * **Format:** YML / XML (`data/models/lbph.yml`).
   * **Input:** $100 \times 100$ Normalized Grayscale.
   * **Distance:** Chi-Square ($0.0 - 150.0$), default threshold $\le 65.0$.
2. **SFace (`sface_recognizer`)**
   * **License:** Apache License 2.0 (OpenCV Zoo).
   * **Format:** ONNX (`face_recognition_sface_2021dec.onnx`).
   * **Input:** $112 \times 112$ Aligned BGR.
   * **Metric:** Cosine Similarity ($[-1.0, 1.0]$), default threshold $\ge 0.363$.

---

## 4. Strict License Governance Rules

> [!IMPORTANT]
> **Library License vs. Model Weight License Distinction:**
> An open-source Python wrapper (e.g. MIT) does **not** grant rights to pretrained weights distributed alongside it if those weights are licensed under non-commercial, academic, or proprietary terms.
> 
> * **OpenCV Zoo Models (YuNet / SFace):** Explicitly distributed under permissive MIT and Apache 2.0 licenses. Approved for DualKey.
> * **InsightFace Default Zoo Models:** Pretrained weights carry non-commercial research restrictions. Prohibited in the DualKey production baseline without explicit commercial licensing.
