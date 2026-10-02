# SPDX-License-Identifier: MIT
"""OpenCV camera adapter -- USB UVC webcam frame acquisition.

Implements CameraPort using cv2.VideoCapture for local webcam access.
Provides frame-rate-aware capture with configurable device index.

Reference: DOC-03-LLD (docs/03-design/low-level-design.md)
"""

from __future__ import annotations

import logging

import cv2
import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)


class OpenCVCameraAdapter:
    """Production camera adapter using OpenCV VideoCapture.

    Wraps cv2.VideoCapture with proper resource lifecycle management
    (open/close) and graceful frame read failure handling.
    """

    def __init__(self, camera_index: int = 0) -> None:
        self._camera_index = camera_index
        self._capture: cv2.VideoCapture | None = None

    def open(self) -> None:
        """Initialize and open the video capture device.

        Tries the specified camera_index first. If that fails, auto-probes
        indices 0..5 to locate an active video capture device.

        Raises:
            RuntimeError: If no working camera device can be opened.
        """
        candidate_indices = [self._camera_index] + [i for i in range(6) if i != self._camera_index]
        for idx in candidate_indices:
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    self._capture = cap
                    self._camera_index = idx
                    logger.info("Camera opened: index=%d", self._camera_index)
                    return
                cap.release()

        self._capture = None
        msg = f"Failed to open any working camera (tested indices {candidate_indices[:4]})"
        raise RuntimeError(msg)

    def read(self) -> NDArray[np.uint8] | None:
        """Capture and return the latest BGR video frame.

        Returns:
            A numpy array of shape (H, W, 3) with dtype uint8,
            or None if frame capture fails.
        """
        if self._capture is None or not self._capture.isOpened():
            return None

        ret, frame = self._capture.read()
        if not ret:
            logger.warning("Frame capture failed on camera %d", self._camera_index)
            return None

        return np.asarray(frame, dtype=np.uint8)

    def close(self) -> None:
        """Release the camera device hardware and free resources."""
        if self._capture is not None:
            self._capture.release()
            self._capture = None
            logger.info("Camera closed: index=%d", self._camera_index)
