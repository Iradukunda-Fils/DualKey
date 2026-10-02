# SPDX-License-Identifier: MIT
"""Face recognizer port — abstract interface for face recognition backends.

Supports both classical (LBPH distance-based) and modern (SFace embedding-based)
recognition through a unified protocol. The port decouples the authorization
domain from any specific OpenCV or ONNX implementation.

Reference: DOC-04-PORTS §2.3 (docs/04-interfaces/internal-interfaces.md)
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class RecognitionResult:
    """Immutable result of a single face recognition evaluation.

    Attributes:
        identity: Resolved person_id, or None if no match found.
        score: Raw distance (LBPH chi-square, lower=better) or similarity
               (SFace cosine, higher=better). Interpretation depends on
               the active backend.
        is_match: True if score passes the backend's configured threshold.
        confidence_level: Human-readable confidence bucket — "HIGH",
                          "MEDIUM", or "LOW".
        model_id: Identifier of the recognizer backend (e.g. "lbph", "sface").
        model_version: Version string (e.g. "1.0.0", "opencv_zoo_2021dec").
        quality_state: Face quality assessment — "USABLE", "BLURRY",
                       or "OCCLUDED".
    """

    identity: str | None
    score: float
    is_match: bool
    confidence_level: str
    model_id: str
    model_version: str
    quality_state: str = "USABLE"


@runtime_checkable
class FaceRecognizerPort(Protocol):
    """Structural interface for face recognition backends.

    Implementations must support both recognition (inference) and enrollment
    (training/prototype computation) workflows.
    """

    def recognize(
        self,
        face_crop: NDArray[np.uint8],
        expected_identity: str | None = None,
    ) -> RecognitionResult:
        """Extract features from a cropped face and match against enrolled identities.

        Args:
            face_crop: Preprocessed face image (grayscale 100x100 for LBPH,
                       aligned BGR 112x112 for SFace).
            expected_identity: Optional hint - the person_id expected from
                               the RFID card. Backends may use this for
                               targeted 1:1 matching vs full 1:N search.

        Returns:
            A RecognitionResult with the match outcome.
        """
        ...

    def enroll(
        self,
        person_id: str,
        face_samples: Sequence[NDArray[np.uint8]],
    ) -> None:
        """Process enrollment samples for a new or updated identity.

        For LBPH: trains the classifier with integer label mapping.
        For SFace: extracts 128D embeddings and computes a normalized
        mean prototype vector. Fine-tuning is PROHIBITED.

        Args:
            person_id: The unique identifier of the person being enrolled.
            face_samples: Sequence of preprocessed face images.
        """
        ...

    def save(self, artifact_path: str) -> None:
        """Serialize trained model or embedding prototypes to disk.

        Args:
            artifact_path: Filesystem path for the output artifact.
        """
        ...

    def load(self, artifact_path: str) -> None:
        """Restore model weights or embedding prototypes from disk.

        Args:
            artifact_path: Filesystem path of the saved artifact.
        """
        ...

    def get_model_info(self) -> tuple[str, str]:
        """Return the recognizer's model identifier and version.

        Returns:
            A tuple of (model_id, model_version).
        """
        ...
