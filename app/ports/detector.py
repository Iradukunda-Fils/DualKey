# SPDX-License-Identifier: MIT
"""Face detector port — abstract interface for face detection in video frames.

Reference: DOC-04-PORTS §2.2 (docs/04-interfaces/internal-interfaces.md)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class DetectedFace:
    """A single detected face in a video frame.

    Attributes:
        bbox: Bounding box as (x, y, width, height) in pixel coordinates.
        confidence: Detection confidence score from the model.
        landmarks: Optional 5-point facial landmarks (eyes, nose, mouth corners)
                   as an Nx2 float32 array. Provided by YuNet; None for Haar.
    """

    bbox: tuple[int, int, int, int]
    confidence: float
    landmarks: NDArray[np.float32] | None = None


@runtime_checkable
class FaceDetectorPort(Protocol):
    """Structural interface for face detection backends.

    Implementations may wrap Haar cascade classifiers, YuNet DNN detectors,
    or any model that locates faces in image frames.
    """

    def detect(self, frame: NDArray[np.uint8]) -> list[DetectedFace]:
        """Detect faces in a BGR or grayscale frame.

        Args:
            frame: Input image as a numpy array.

        Returns:
            A list of DetectedFace instances found in the frame.
            Empty list if no faces are detected.
        """
        ...

    def get_model_info(self) -> tuple[str, str]:
        """Return the detector's model identifier and version.

        Returns:
            A tuple of (model_id, model_version), e.g.
            ("haar_frontalface", "opencv_4.x") or
            ("yunet_face_detection", "2023mar").
        """
        ...
