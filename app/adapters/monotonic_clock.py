# SPDX-License-Identifier: MIT
"""Monotonic clock adapter -- thin wrapper around time.monotonic().

Exists solely to satisfy the ClockPort protocol, enabling deterministic
testing of deadline-sensitive logic by swapping in a fake clock.
"""

from __future__ import annotations

import time


class MonotonicClock:
    """Production clock adapter using the OS monotonic timer."""

    def now_monotonic(self) -> float:
        """Return the current monotonic time in seconds."""
        return time.monotonic()
