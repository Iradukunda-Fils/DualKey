# SPDX-License-Identifier: MIT
"""Clock port — abstract interface for monotonic time.

Wrapping the system clock behind a port enables deterministic testing
of deadline-sensitive authorization logic without real-time delays.

Reference: DOC-04-PORTS §2.6 (docs/04-interfaces/internal-interfaces.md)
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ClockPort(Protocol):
    """Structural interface for monotonic time acquisition.

    The authorization policy and session lifecycle depend on monotonic
    time (not wall-clock time) to prevent time-zone or NTP drift from
    affecting deadline enforcement.
    """

    def now_monotonic(self) -> float:
        """Return the current monotonic time in seconds.

        The returned value has no defined epoch — only differences
        between calls are meaningful.

        Returns:
            A monotonically increasing float timestamp in seconds.
        """
        ...
