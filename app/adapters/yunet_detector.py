# SPDX-License-Identifier: MIT
"""YuNet DNN face detector adapter.

Implements FaceDetectorPort using OpenCV's cv2.FaceDetectorYN for
modern, lightweight face detection with 5-point facial landmarks.
Requires the ONNX model file (MIT licensed from OpenCV Zoo).

Reference: DOC-03-FACE (docs/03-design/face-recognition.md)
           ADR-0007 (docs/08-decisions/ADR-0007-pluggable-face-recognition-strategy.md)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

from app.ports.detector import DetectedFace

logger = logging.getLogger(__name__)

_MODEL_ID = "yunet_face_detection"
_MODEL_VERSION = "2023mar"


class YuNetFaceDetector:
    """YuNet DNN face detector using OpenCV's FaceDetectorYN.

    Provides higher accuracy than Haar cascades with 5-point facial
    landmarks (left eye, right eye, nose tip, left mouth, right mouth)
    needed for SFace alignment.
    """

    def __init__(
        self,
        model_path: str,
        input_size: tuple[int, int] = (320, 320),
        score_threshold: float = 0.9,
        nms_threshold: float = 0.3,
        top_k: int = 5000,
    ) -> None:
        if not Path(model_path).exists():
            msg = f"YuNet model file not found: {model_path}"
            raise FileNotFoundError(msg)

        self._input_size = input_size
        self._detector: Any = cv2.FaceDetectorYN.create(
            model=model_path,
            config="",
            input_size=input_size,
            score_threshold=score_threshold,
            nms_threshold=nms_threshold,
            top_k=top_k,
        )
        logger.info("YuNet detector loaded: %s (input=%s)", model_path, input_size)

    def detect(self, frame: NDArray[np.uint8]) -> list[DetectedFace]:
        """Detect faces in a BGR frame with 5-point landmarks.

        Args:
            frame: BGR input image.

        Returns:
            A list of DetectedFace instances with landmarks.
        """
        h, w = frame.shape[:2]
        if (w, h) != self._input_size:
            self._detector.setInputSize((w, h))

        _, raw_detections = self._detector.detect(frame)

        if raw_detections is None or len(raw_detections) == 0:
            return []

        faces: list[DetectedFace] = []
        for det in raw_detections:
            # YuNet output: [x, y, w, h, x_re, y_re, x_le, y_le,
            #                x_nt, y_nt, x_rcm, y_rcm, x_lcm, y_lcm, score]
            x = int(det[0])
            y = int(det[1])
            bw = int(det[2])
            bh = int(det[3])
            score = float(det[14])

            landmarks = np.array([
                [float(det[4]), float(det[5])],    # right eye
                [float(det[6]), float(det[7])],    # left eye
                [float(det[8]), float(det[9])],    # nose tip
                [float(det[10]), float(det[11])],  # right mouth corner
                [float(det[12]), float(det[13])],  # left mouth corner
            ], dtype=np.float32)

            faces.append(DetectedFace(
                bbox=(x, y, bw, bh),
                confidence=score,
                landmarks=landmarks,
            ))

        return faces

    def get_model_info(self) -> tuple[str, str]:
        """Return the detector model identifier and version."""
        return _MODEL_ID, _MODEL_VERSION
