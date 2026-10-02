# Identity Enrollment & Model Training Specification

**Document ID:** `DOC-03-ENROLL`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Enrollment Overview & Architecture

Enrollment is an administrative workflow that securely links a physical card token to an individual's biometric template. DualKey strictly mandates multi-sample collection to build an expressive LBPH histogram representation.

```text
[Operator CLI: python -m app.main --enroll]
                  │
                  ▼
  [Step 1: Input Identity Metadata]
  - Enter Display Name (e.g. "Alice Smith")
  - System generates unique person_id (UUIDv4) and integer face_label
                  │
                  ▼
  [Step 2: Read Physical RFID Token]
  - Operator taps user card on MFRC522 reader
  - ESP32 emits rfid_detected; Host records card_uid
                  │
                  ▼
  [Step 3: Multi-Sample Face Acquisition]
  - Camera acquires stream; rejects frames unless exactly 1 face is visible
  - Captures N samples (default N = 20) across slight angle/expression variations
                  │
                  ▼
  [Step 4: Image Normalization & Disk Archiving]
  - Crop face ROI, resize to 100x100, apply equalizeHist
  - Save to data/faces/<person_id>/sample_001.png ... sample_020.png
                  │
                  ▼
  [Step 5: LBPH Model Training & Serialization]
  - Load all labeled face samples across all enrolled users
  - Train cv2.face.LBPHFaceRecognizer
  - Serialize model to data/models/lbph.yml
                  │
                  ▼
  [Step 6: Atomic SQLite Persistence]
  - Insert record into 'persons' table
  - Insert record into 'rfid_cards' table bound to person_id
                  │
                  ▼
  [Step 7: Mandatory Live Verification Gate]
  - Prompt user to perform a live test tap and face verification
  - Card/identity activated only upon successful pass of live test
```

---

## 2. Multi-Sample Rule & Quality Standards

> [!IMPORTANT]
> **Single Photograph Prohibition:** The enrollment pipeline shall not permit training an identity from a single photographic snapshot. Single images do not provide sufficient texture variance across head orientations and subtle lighting shifts, leading to brittle recognition and high false-rejection rates.

### Capture Guidelines
* **Sample Count:** Minimum 15 samples, recommended 20 samples per enrolled individual.
* **Orientation Variation:**
  * 5 samples looking directly into the camera lens (frontal neutral).
  * 3 samples with slight head tilt left ($\approx 10^\circ$).
  * 3 samples with slight head tilt right ($\approx 10^\circ$).
  * 3 samples with slight head tilt upward ($\approx 5^\circ$).
  * 3 samples with slight head tilt downward ($\approx 5^\circ$).
  * 3 samples with slight facial expression variation (smiling, speaking).
* **Quality Filtering:** Frames where face bounding box is smaller than $120 \times 120$ pixels in the $640 \times 480$ frame are automatically discarded as too distant.

---

## 3. Storage & Metadata Management

### Filesystem Storage
Raw normalized PNG images are preserved in the data directory:
```text
data/
└── faces/
    ├── 550e8400-e29b-41d4-a716-446655440000/    # person_id
    │   ├── sample_001.png
    │   ├── sample_002.png
    │   └── ...
    └── b72e8111-c11a-42a1-b918-112233445566/
        ├── sample_001.png
        └── ...
```

### Relational Binding (SQLite)
The label integer required by OpenCV (`int`) is persistently mapped to the application's UUID `person_id` in SQLite:
```sql
INSERT INTO persons (person_id, display_name, face_label, status, created_at)
VALUES ('550e8400-e29b-41d4-a716-446655440000', 'Alice Smith', 1, 'ACTIVE', 1727650000.0);

INSERT INTO rfid_cards (rfid_uid, person_id, status, enrolled_at)
VALUES ('A1B2C3D4', '550e8400-e29b-41d4-a716-446655440000', 'ACTIVE', 1727650000.0);
```

### 3.1 Model Artifact Updating & Invariant

DualKey supports dual enrollment artifact updates depending on the active or supported recognizers:

1. **For LBPH Recognizer:**
   * Reads all labeled sample crops across all enrolled users.
   * Retrains `cv2.face.LBPHFaceRecognizer`.
   * Atomically overwrites `data/models/lbph.yml`.

2. **For SFace Recognizer (Embedding Prototypes):**
   * Computes 128D embeddings for each new sample using pretrained `FaceRecognizerSF`.
   * Averages embeddings into an identity prototype vector: $\mathbf{p} = \text{mean}(\mathbf{e}_1, \dots, \mathbf{e}_M)$.
   * Normalizes prototype to unit length: $\mathbf{p} \leftarrow \mathbf{p} / \|\mathbf{p}\|_2$.
   * Saves prototypes into `data/models/sface_prototypes.json` or SQLite without modifying base model weights.
   * **No fine-tuning of the deep model is executed.**

### 3.2 Rollback Safety
Whenever a user is added, updated, or removed, the `EnrollmentService` updates the corresponding artifacts. If artifact serialization fails, the database transaction is rolled back, preventing orphaned records or desynchronized biometric models.
