# SPDX-License-Identifier: MIT
"""Camera port — abstract interface for video frame acquisition.

Reference: DOC-04-PORTS §2.1 (docs/04-interfaces/internal-interfaces.md)
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np
from numpy.typing import NDArray

Frame = NDArray[np.uint8]
"""A single video frame in BGR uint8 format (H x W x 3)."""


@runtime_checkable
class CameraPort(Protocol):
    """Structural interface for video capture devices.

    Adapters implementing this port must provide non-blocking frame
    acquisition from a camera source (USB UVC, file, or virtual device).
    """

    def open(self) -> None:
        """Initialize and open the video capture device.

        Raises:
            RuntimeError: If the device cannot be opened.
        """
        ...

    def read(self) -> Frame | None:
        """Capture and return the latest video frame in BGR format.

        Returns:
            A numpy array of shape (H, W, 3) with dtype uint8, or None
            if frame capture fails (device disconnected, buffer empty).
        """
        ...

    def close(self) -> None:
        """Release the camera device hardware and free resources."""
        ...
