# SPDX-License-Identifier: MIT
"""ESP32 serial transport adapter -- NDJSON communication over USB CDC UART.

Implements the DeviceTransportPort protocol for physical ESP32 communication.
Messages are framed as newline-delimited JSON (NDJSON) at 115200 baud, 8N1.
Each message is <= 512 bytes and carries a protocol version ("v": 1).

Reference: DOC-04-SERIAL (docs/04-interfaces/serial-message-contract.md)
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, cast

import serial

from app.ports.device_transport import DeviceCommand, DeviceEvent

logger = logging.getLogger(__name__)

_MAX_FRAME_BYTES: int = 512
_PROTOCOL_VERSION: int = 1


class Esp32SerialAdapter:
    """Non-blocking NDJSON serial transport for ESP32 communication.

    Buffers incoming bytes, splits on newline boundaries, and parses
    each complete line as JSON. Malformed lines are logged and discarded.
    """

    def __init__(
        self,
        port: str = "/dev/ttyUSB0",
        baud: int = 115200,
        timeout: float = 0.05,
    ) -> None:
        self._port = port
        self._baud = baud
        self._timeout = timeout
        self._serial: serial.Serial | None = None
        self._buffer: str = ""
        self._last_executed_id: str | None = None

    def open(self) -> None:
        """Open the serial connection to the ESP32.

        Attempts to open the configured port first. If port is 'auto' or opening
        fails due to device name mismatch (e.g. /dev/ttyACM0 vs /dev/ttyUSB0),
        automatically scans system ports for active USB-to-UART devices.
        """
        resolved_port = self._resolve_port(self._port)
        try:
            self._serial = serial.Serial(
                port=resolved_port,
                baudrate=self._baud,
                timeout=self._timeout,
            )
            self._port = resolved_port
            time.sleep(0.05)
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()
            logger.info("Serial connection opened: %s @ %d baud", self._port, self._baud)
        except (serial.SerialException, FileNotFoundError) as err:
            logger.warning(
                "Failed to open primary port %s (%s) -- attempting auto-discovery",
                self._port,
                err,
            )
            fallback_port = self._auto_discover_port()
            if fallback_port and fallback_port != resolved_port:
                self._serial = serial.Serial(
                    port=fallback_port,
                    baudrate=self._baud,
                    timeout=self._timeout,
                )
                self._port = fallback_port
                time.sleep(0.05)
                self._serial.reset_input_buffer()
                self._serial.reset_output_buffer()
                logger.info(
                    "Auto-discovered serial connection opened: %s @ %d baud",
                    self._port,
                    self._baud,
                )
            else:
                raise

    @staticmethod
    def _resolve_port(configured_port: str) -> str:
        """Resolve port string, performing auto-discovery if set to 'auto'."""
        if configured_port.lower() == "auto":
            discovered = Esp32SerialAdapter._auto_discover_port()
            return discovered if discovered else "/dev/ttyUSB0"
        return configured_port

    @staticmethod
    def _auto_discover_port() -> str | None:
        """Scan system for connected ESP32 USB-to-UART serial ports."""
        try:
            import serial.tools.list_ports
            ports = list(serial.tools.list_ports.comports())
            for p in ports:
                # Common patterns (Linux: ttyUSB/ttyACM, macOS: cu.usbserial, Win: COM)
                dev = p.device
                desc = (p.description or "").lower()
                hwid = (p.hwid or "").lower()
                if any(k in dev for k in ("ttyUSB", "ttyACM", "usbserial", "COM")) or \
                   any(k in desc or k in hwid for k in ("cp210", "ch340", "ftdi", "esp32", "uart")):
                    logger.info(
                        "Discovered USB serial device candidate: %s (%s)", dev, p.description
                    )
                    return dev
        except Exception as e:
            logger.debug("Serial auto-discovery failed: %s", e)
        return None

    def close(self) -> None:
        """Close the serial connection and clear the buffer."""
        if self._serial is not None and self._serial.is_open:
            self._serial.close()
        self._serial = None
        self._buffer = ""
        logger.info("Serial connection closed")

    def is_connected(self) -> bool:
        """Return True if the serial port is open and active."""
        return self._serial is not None and self._serial.is_open

    def send_access_command(self, command: DeviceCommand) -> None:
        """Serialize and transmit an access command as NDJSON.

        Args:
            command: The DeviceCommand to send.

        Raises:
            ConnectionError: If the serial link is not connected.
        """
        if not self.is_connected() or self._serial is None:
            raise ConnectionError("Serial port is not connected")

        message: dict[str, Any] = {
            "v": _PROTOCOL_VERSION,
            "type": "access_command",
            "command_id": command.command_id,
            "session_id": command.session_id,
            "decision": command.decision,
            "reason": command.reason,
            "door_hold_ms": command.door_hold_ms,
        }

        frame = json.dumps(message, separators=(",", ":")) + "\n"
        frame_bytes = frame.encode("utf-8")

        if len(frame_bytes) > _MAX_FRAME_BYTES:
            logger.error(
                "Frame exceeds %d bytes (%d), dropping", _MAX_FRAME_BYTES, len(frame_bytes)
            )
            return

        self._serial.write(frame_bytes)
        self._serial.flush()
        logger.debug("Sent: %s", frame.strip())

    def poll(self) -> list[DeviceEvent]:
        """Poll for incoming NDJSON messages from the ESP32.

        Non-blocking: reads available bytes, appends to internal buffer,
        splits on newline, and parses each complete line.

        Returns:
            A list of parsed DeviceEvent instances. Empty if no complete
            messages are available.
        """
        if not self.is_connected() or self._serial is None:
            return []

        # Read available bytes without blocking
        available = self._serial.in_waiting
        if available > 0:
            raw = self._serial.read(available)
            self._buffer += raw.decode("utf-8", errors="replace")

        # Split on newline boundaries
        events: list[DeviceEvent] = []
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.strip()
            if not line:
                continue

            event = self._parse_line(line)
            if event is not None:
                events.append(event)

        return events

    def _parse_line(self, line: str) -> DeviceEvent | None:
        """Parse a single NDJSON line into a DeviceEvent.

        Returns None and logs a warning if parsing fails.
        """
        try:
            parsed: object = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            logger.debug("Malformed JSON discarded: %s", line[:80])
            return None

        if not isinstance(parsed, dict):
            logger.warning("Expected JSON object, got: %s", type(parsed).__name__)
            return None

        data = cast(dict[str, Any], parsed)

        version = data.get("v")
        if version != _PROTOCOL_VERSION:
            logger.warning("Unknown protocol version: %s", version)
            return None

        msg_type = data.get("type")
        if not isinstance(msg_type, str):
            logger.warning("Missing or invalid 'type' field")
            return None

        event_id = data.get("event_id") or data.get("command_id") or str(uuid.uuid4())

        return DeviceEvent(
            event_type=msg_type,
            payload=data,
            event_id=str(event_id),
        )
