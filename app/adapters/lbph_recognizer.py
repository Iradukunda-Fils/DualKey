# SPDX-License-Identifier: MIT
"""LBPH face recognizer adapter -- OpenCV Local Binary Patterns Histograms.

Implements FaceRecognizerPort using cv2.face.LBPHFaceRecognizer for the
MVP educational baseline. Face crops are resized to 100x100 grayscale,
histogram-equalized, and matched using chi-square distance.

Reference: DOC-03-FACE (docs/03-design/face-recognition.md)
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

from app.ports.recognizer import RecognitionResult

logger = logging.getLogger(__name__)

_MODEL_ID = "lbph_recognizer"
_MODEL_VERSION = "1.0.0"
_CROP_SIZE = (100, 100)


class LBPHRecognizer:
    """LBPH face recognizer using OpenCV's LBPHFaceRecognizer.

    Enrollment trains the classifier with integer labels mapped to person_ids.
    Recognition predicts the label and returns the chi-square distance.

    The label-to-person_id mapping is managed externally via the
    IdentityRepository (get_person_by_label).
    """

    def __init__(
        self,
        threshold: float = 65.0,
        radius: int = 1,
        neighbors: int = 8,
        grid_x: int = 8,
        grid_y: int = 8,
    ) -> None:
        self._threshold = threshold
        self._recognizer: Any = cv2.face.LBPHFaceRecognizer_create(  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType]
            radius=radius,
            neighbors=neighbors,
            grid_x=grid_x,
            grid_y=grid_y,
            threshold=float("inf"),  # We handle threshold ourselves
        )
        self._trained = False
        self._label_to_person: dict[int, str] = {}

    def recognize(
        self,
        face_crop: NDArray[np.uint8],
        expected_identity: str | None = None,
    ) -> RecognitionResult:
        """Recognize a face crop against enrolled identities.

        Args:
            face_crop: Grayscale or BGR face image (will be preprocessed).
            expected_identity: Unused in LBPH (performs 1:N search).

        Returns:
            A RecognitionResult with the closest match and distance.
        """
        if not self._trained:
            return RecognitionResult(
                identity=None,
                score=float("inf"),
                is_match=False,
                confidence_level="LOW",
                model_id=_MODEL_ID,
                model_version=_MODEL_VERSION,
                quality_state="USABLE",
            )

        preprocessed = self._preprocess(face_crop)
        raw_label, raw_distance = self._recognizer.predict(preprocessed)
        label = int(raw_label)
        distance = float(raw_distance)

        person_id = self._label_to_person.get(label)
        is_match = distance <= self._threshold and person_id is not None
        confidence_level = self._classify_confidence(distance)

        return RecognitionResult(
            identity=person_id,
            score=distance,
            is_match=is_match,
            confidence_level=confidence_level,
            model_id=_MODEL_ID,
            model_version=_MODEL_VERSION,
            quality_state="USABLE",
        )

    def enroll(
        self,
        person_id: str,
        face_samples: Sequence[NDArray[np.uint8]],
    ) -> None:
        """Train the LBPH classifier with face samples for a person.

        Each call to enroll adds samples to the existing training set
        and retrains the full classifier.

        Args:
            person_id: The person's unique identifier.
            face_samples: Sequence of face images to train on.
        """
        label = self._get_or_assign_label(person_id)

        preprocessed = [self._preprocess(s) for s in face_samples]
        labels = np.array([label] * len(preprocessed), dtype=np.int32)

        if self._trained:
            self._recognizer.update(preprocessed, labels)
        else:
            self._recognizer.train(preprocessed, labels)
            self._trained = True

        logger.info(
            "Enrolled %d samples for %s (label=%d)", len(face_samples), person_id, label
        )

    def save(self, artifact_path: str) -> None:
        """Save the trained LBPH model to disk."""
        if not self._trained:
            logger.warning("Cannot save untrained model")
            return
        self._recognizer.save(artifact_path)
        logger.info("LBPH model saved to %s", artifact_path)

    def load(self, artifact_path: str) -> None:
        """Load a previously trained LBPH model from disk."""
        self._recognizer.read(artifact_path)
        self._trained = True
        logger.info("LBPH model loaded from %s", artifact_path)

    def get_model_info(self) -> tuple[str, str]:
        """Return the recognizer model identifier and version."""
        return _MODEL_ID, _MODEL_VERSION

    def set_label_mapping(self, mapping: dict[int, str]) -> None:
        """Set the label-to-person_id mapping from the IdentityRepository.

        This must be called after loading a model to restore the mapping.

        Args:
            mapping: Dictionary of {face_label: person_id}.
        """
        self._label_to_person = dict(mapping)

    def _get_or_assign_label(self, person_id: str) -> int:
        """Get existing label or assign the next available one."""
        for label, pid in self._label_to_person.items():
            if pid == person_id:
                return label

        label = len(self._label_to_person)
        self._label_to_person[label] = person_id
        return label

    @staticmethod
    def _preprocess(face: NDArray[np.uint8]) -> NDArray[np.uint8]:
        """Normalize a face crop to 100x100 equalized grayscale."""
        gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY) if len(face.shape) == 3 else face
        resized = cv2.resize(gray, _CROP_SIZE, interpolation=cv2.INTER_AREA)
        equalized = np.asarray(cv2.equalizeHist(resized), dtype=np.uint8)
        return equalized

    @staticmethod
    def _classify_confidence(distance: float) -> str:
        """Classify chi-square distance into human-readable confidence."""
        if distance <= 40.0:
            return "HIGH"
        if distance <= 65.0:
            return "MEDIUM"
        return "LOW"
