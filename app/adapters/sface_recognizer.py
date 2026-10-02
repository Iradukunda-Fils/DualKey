# SPDX-License-Identifier: MIT
"""SFace deep face recognizer adapter.

Implements FaceRecognizerPort using OpenCV's cv2.FaceRecognizerSF for
modern 128-dimensional embedding-based face recognition. Uses cosine
similarity with prototype averaging -- NO fine-tuning.

Enrollment pattern (from ADR-0007):
    1. Extract 128D L2-normalized embedding per sample
    2. Compute mean vector: p = mean(e_1..e_M)
    3. L2-normalize prototype: p <- p / ||p||_2
    4. Store in sface_prototypes.json
    5. At inference: cosine_similarity = dot(test, prototype) >= threshold

Reference: DOC-03-FACE (docs/03-design/face-recognition.md)
           ADR-0007 (docs/08-decisions/ADR-0007-pluggable-face-recognition-strategy.md)
"""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

from app.ports.recognizer import RecognitionResult

logger = logging.getLogger(__name__)

_MODEL_ID = "sface_recognizer"
_MODEL_VERSION = "opencv_zoo_2021dec"
_ALIGNED_SIZE = (112, 112)


class SFaceRecognizer:
    """SFace embedding-based face recognizer using OpenCV FaceRecognizerSF.

    Uses pretrained ONNX model to extract 128D face embeddings.
    Enrollment computes a normalized mean prototype per identity.
    Recognition uses cosine similarity against stored prototypes.
    Fine-tuning is PROHIBITED per ADR-0007.
    """

    def __init__(
        self,
        model_path: str,
        threshold: float = 0.363,
    ) -> None:
        if not Path(model_path).exists():
            msg = f"SFace model file not found: {model_path}"
            raise FileNotFoundError(msg)

        self._threshold = threshold
        self._recognizer: Any = cv2.FaceRecognizerSF.create(
            model=model_path,
            config="",
        )
        # person_id -> L2-normalized 128D prototype embedding
        self._prototypes: dict[str, NDArray[np.float32]] = {}
        logger.info("SFace recognizer loaded: %s (threshold=%.3f)", model_path, threshold)

    def recognize(
        self,
        face_crop: NDArray[np.uint8],
        expected_identity: str | None = None,
    ) -> RecognitionResult:
        """Match a face crop against enrolled prototype embeddings.

        Args:
            face_crop: Aligned BGR face image (112x112 preferred).
            expected_identity: If provided, performs targeted 1:1 match
                               against this identity's prototype only.

        Returns:
            RecognitionResult with cosine similarity score.
        """
        if not self._prototypes:
            return RecognitionResult(
                identity=None,
                score=0.0,
                is_match=False,
                confidence_level="LOW",
                model_id=_MODEL_ID,
                model_version=_MODEL_VERSION,
            )

        preprocessed = self._preprocess(face_crop)
        embedding = self._extract_embedding(preprocessed)

        if expected_identity is not None and expected_identity in self._prototypes:
            prototype = self._prototypes[expected_identity]
            similarity = float(np.dot(embedding, prototype))
            is_match = similarity >= self._threshold
            return RecognitionResult(
                identity=expected_identity if is_match else None,
                score=similarity,
                is_match=is_match,
                confidence_level=self._classify_confidence(similarity),
                model_id=_MODEL_ID,
                model_version=_MODEL_VERSION,
            )

        # 1:N search across all prototypes
        best_id: str | None = None
        best_similarity = -1.0

        for person_id, prototype in self._prototypes.items():
            similarity = float(np.dot(embedding, prototype))
            if similarity > best_similarity:
                best_similarity = similarity
                best_id = person_id

        is_match = best_similarity >= self._threshold
        return RecognitionResult(
            identity=best_id if is_match else None,
            score=best_similarity,
            is_match=is_match,
            confidence_level=self._classify_confidence(best_similarity),
            model_id=_MODEL_ID,
            model_version=_MODEL_VERSION,
        )

    def enroll(
        self,
        person_id: str,
        face_samples: Sequence[NDArray[np.uint8]],
    ) -> None:
        """Compute a normalized mean prototype embedding from samples.

        NO fine-tuning -- uses the pretrained model as a fixed feature
        extractor. This is the correct engineering pattern for small
        populations per ADR-0007.

        Args:
            person_id: Unique identifier of the person.
            face_samples: Aligned BGR face images.
        """
        embeddings: list[NDArray[np.float32]] = []
        for sample in face_samples:
            preprocessed = self._preprocess(sample)
            emb = self._extract_embedding(preprocessed)
            embeddings.append(emb)

        stacked = np.stack(embeddings)
        mean_embedding: NDArray[np.float32] = np.mean(stacked, axis=0)
        norm = float(np.linalg.norm(mean_embedding))
        if norm > 0:
            mean_embedding = mean_embedding / np.float32(norm)

        self._prototypes[person_id] = mean_embedding
        logger.info(
            "Enrolled SFace prototype for %s from %d samples", person_id, len(face_samples)
        )

    def save(self, artifact_path: str) -> None:
        """Save prototype embeddings to a JSON file.

        Atomic write via temp file + rename to prevent corruption.
        """
        data: dict[str, list[float]] = {
            pid: proto.tolist() for pid, proto in self._prototypes.items()
        }
        tmp_path = artifact_path + ".tmp"
        Path(tmp_path).write_text(json.dumps(data, indent=2), encoding="utf-8")
        Path(tmp_path).replace(artifact_path)
        logger.info("SFace prototypes saved to %s (%d identities)", artifact_path, len(data))

    def load(self, artifact_path: str) -> None:
        """Load prototype embeddings from a JSON file."""
        raw = json.loads(Path(artifact_path).read_text(encoding="utf-8"))
        self._prototypes = {
            pid: np.array(vec, dtype=np.float32) for pid, vec in raw.items()
        }
        logger.info(
            "SFace prototypes loaded from %s (%d identities)", artifact_path, len(self._prototypes)
        )

    def get_model_info(self) -> tuple[str, str]:
        """Return the recognizer model identifier and version."""
        return _MODEL_ID, _MODEL_VERSION

    def _extract_embedding(self, face: NDArray[np.uint8]) -> NDArray[np.float32]:
        """Extract and L2-normalize a 128D embedding from a face image."""
        raw_feature = self._recognizer.feature(face)
        embedding: NDArray[np.float32] = np.asarray(raw_feature, dtype=np.float32).flatten()
        norm = float(np.linalg.norm(embedding))
        if norm > 0:
            embedding = embedding / np.float32(norm)
        return embedding

    @staticmethod
    def _preprocess(face: NDArray[np.uint8]) -> NDArray[np.uint8]:
        """Resize to 112x112 BGR for SFace input."""
        if len(face.shape) == 2:
            face = np.asarray(cv2.cvtColor(face, cv2.COLOR_GRAY2BGR), dtype=np.uint8)
        resized = np.asarray(
            cv2.resize(face, _ALIGNED_SIZE, interpolation=cv2.INTER_LINEAR), dtype=np.uint8
        )
        return resized

    @staticmethod
    def _classify_confidence(similarity: float) -> str:
        """Classify cosine similarity into human-readable confidence."""
        if similarity >= 0.5:
            return "HIGH"
        if similarity >= 0.363:
            return "MEDIUM"
        return "LOW"
