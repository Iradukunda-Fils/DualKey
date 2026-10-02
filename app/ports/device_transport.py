# SPDX-License-Identifier: MIT
"""Device transport port — abstract interface for ESP32 serial communication.

Reference: DOC-04-PORTS §2.3 (docs/04-interfaces/internal-interfaces.md)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class DeviceEvent:
    """An incoming event from the ESP32 microcontroller.

    Attributes:
        event_type: Message type — "rfid_detected", "command_result",
                    or "heartbeat".
        payload: Parsed NDJSON payload as a dictionary.
        event_id: Unique correlation identifier from the device.
    """

    event_type: str
    payload: dict[str, Any]
    event_id: str


@dataclass(frozen=True)
class DeviceCommand:
    """An outgoing access command to the ESP32 microcontroller.

    Attributes:
        command_id: Unique correlation identifier for tracking acknowledgement.
        session_id: The access session that triggered this command.
        decision: "grant" or "deny".
        reason: Machine-readable ReasonCode string value.
        door_hold_ms: Duration in milliseconds for the servo to remain open
                      (only meaningful when decision is "grant").
    """

    command_id: str
    session_id: str
    decision: str
    reason: str
    door_hold_ms: int


@runtime_checkable
class DeviceTransportPort(Protocol):
    """Structural interface for ESP32 serial communication.

    Implementations handle NDJSON framing, line buffering, correlation
    tracking, and physical UART management.
    """

    def send_access_command(self, command: DeviceCommand) -> None:
        """Dispatch an access command to the microcontroller.

        The command is serialized to NDJSON and transmitted over the
        physical serial link.

        Args:
            command: The access command to send.

        Raises:
            ConnectionError: If the serial link is down.
        """
        ...

    def poll(self) -> list[DeviceEvent]:
        """Poll buffered incoming messages and return parsed device events.

        Non-blocking: returns an empty list if no messages are available.

        Returns:
            A list of parsed DeviceEvent instances.
        """
        ...

    def is_connected(self) -> bool:
        """Return True if the physical serial connection is open and active."""
        ...
