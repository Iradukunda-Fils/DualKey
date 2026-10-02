# SPDX-License-Identifier: MIT
"""Haar cascade face detector adapter.

Implements FaceDetectorPort using OpenCV's bundled Haar cascade classifier
for frontal face detection. This is the MVP baseline detector -- lightweight,
CPU-only, no external model download required.

Reference: DOC-03-FACE (docs/03-design/face-recognition.md)
"""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from app.ports.detector import DetectedFace

logger = logging.getLogger(__name__)

_MODEL_ID = "haar_frontalface"
_MODEL_VERSION = "opencv_4.x"


class HaarFaceDetector:
    """Haar cascade frontal face detector.

    Uses the bundled haarcascade_frontalface_default.xml classifier.
    Input frames are converted to grayscale and histogram-equalized
    before detection to improve robustness to lighting variation.
    """

    def __init__(
        self,
        scale_factor: float = 1.1,
        min_neighbors: int = 5,
        min_size: tuple[int, int] = (60, 60),
        cascade_path: str | None = None,
    ) -> None:
        resolved_path = self._resolve_cascade_path(cascade_path)
        self._classifier = cv2.CascadeClassifier(resolved_path)

        if self._classifier.empty():
            msg = f"Failed to load Haar cascade from: {resolved_path}"
            raise RuntimeError(msg)

        self._scale_factor = scale_factor
        self._min_neighbors = min_neighbors
        self._min_size = min_size
        logger.info("Haar detector loaded: %s", resolved_path)

    @staticmethod
    def _resolve_cascade_path(custom_path: str | None) -> str:
        """Resolve the haarcascade_frontalface_default.xml path from candidate locations."""
        if custom_path and Path(custom_path).exists():
            return custom_path

        candidates = [
            "models/lbph/haarcascade_frontalface_default.xml",
            str(cv2.data.haarcascades) + "haarcascade_frontalface_default.xml",  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType, reportUnknownArgumentType]
            "/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml",
            "/usr/share/opencv/haarcascades/haarcascade_frontalface_default.xml",
        ]

        for path in candidates:
            if Path(path).exists():
                return path

        # Fallback to cv2 data path string if none found on disk
        return str(cv2.data.haarcascades) + "haarcascade_frontalface_default.xml"  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType, reportUnknownArgumentType]

    def detect(self, frame: NDArray[np.uint8]) -> list[DetectedFace]:
        """Detect faces in a BGR or grayscale frame.

        Args:
            frame: Input image as a numpy array.

        Returns:
            A list of DetectedFace instances. Empty if no faces found.
        """
        # Convert to grayscale if needed
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame

        # Histogram equalization for lighting robustness
        gray = cv2.equalizeHist(gray)

        rects = self._classifier.detectMultiScale(
            gray,
            scaleFactor=self._scale_factor,
            minNeighbors=self._min_neighbors,
            minSize=self._min_size,
        )

        if len(rects) == 0:
            return []

        faces: list[DetectedFace] = []
        for x, y, w, h in rects:
            faces.append(
                DetectedFace(
                    bbox=(int(x), int(y), int(w), int(h)),
                    confidence=1.0,  # Haar does not provide confidence
                    landmarks=None,
                )
            )

        return faces

    def get_model_info(self) -> tuple[str, str]:
        """Return the detector model identifier and version."""
        return _MODEL_ID, _MODEL_VERSION
