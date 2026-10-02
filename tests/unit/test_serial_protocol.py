# SPDX-License-Identifier: MIT
"""Unit tests for NDJSON serial protocol parsing and framing.

Tests the core parsing logic of Esp32SerialAdapter without requiring
a physical serial port -- exercises malformed JSON handling, protocol
version validation, and buffer splitting.
"""

from __future__ import annotations

import json

from app.adapters.esp32_serial import Esp32SerialAdapter


class FakeSerial:
    """In-memory fake serial port for testing without hardware."""

    def __init__(self) -> None:
        self._input_buffer: bytes = b""
        self._output_buffer: bytes = b""
        self.is_open: bool = True

    @property
    def in_waiting(self) -> int:
        return len(self._input_buffer)

    def read(self, size: int) -> bytes:
        data = self._input_buffer[:size]
        self._input_buffer = self._input_buffer[size:]
        return data

    def write(self, data: bytes) -> int:
        self._output_buffer += data
        return len(data)

    def flush(self) -> None:
        pass

    def close(self) -> None:
        self.is_open = False

    def inject(self, data: str) -> None:
        """Inject data into the input buffer as if received from ESP32."""
        self._input_buffer += data.encode("utf-8")

    def get_output(self) -> str:
        """Get all data written to the port."""
        return self._output_buffer.decode("utf-8")


def _make_adapter_with_fake() -> tuple[Esp32SerialAdapter, FakeSerial]:
    """Create an Esp32SerialAdapter wired to a FakeSerial."""
    adapter = Esp32SerialAdapter()
    fake = FakeSerial()
    adapter._serial = fake  # type: ignore[assignment]
    return adapter, fake


class TestNdjsonParsing:
    """Test NDJSON line parsing for various message types."""

    def test_parse_rfid_detected_event(self) -> None:
        adapter, fake = _make_adapter_with_fake()
        msg = json.dumps({
            "v": 1,
            "type": "rfid_detected",
            "event_id": "evt-001",
            "uid": "AABBCCDD",
        })
        fake.inject(msg + "\n")

        events = adapter.poll()
        assert len(events) == 1
        assert events[0].event_type == "rfid_detected"
        assert events[0].event_id == "evt-001"
        assert events[0].payload["uid"] == "AABBCCDD"

    def test_parse_heartbeat_event(self) -> None:
        adapter, fake = _make_adapter_with_fake()
        msg = json.dumps({
            "v": 1,
            "type": "heartbeat",
            "event_id": "hb-001",
            "uptime_ms": 12345,
        })
        fake.inject(msg + "\n")

        events = adapter.poll()
        assert len(events) == 1
        assert events[0].event_type == "heartbeat"

    def test_parse_command_result_event(self) -> None:
        adapter, fake = _make_adapter_with_fake()
        msg = json.dumps({
            "v": 1,
            "type": "command_result",
            "command_id": "cmd-001",
            "status": "executed",
        })
        fake.inject(msg + "\n")

        events = adapter.poll()
        assert len(events) == 1
        assert events[0].event_type == "command_result"
        assert events[0].event_id == "cmd-001"


class TestMalformedInput:
    """Test graceful handling of malformed or invalid input."""

    def test_malformed_json_is_discarded(self) -> None:
        adapter, fake = _make_adapter_with_fake()
        fake.inject("not valid json\n")

        events = adapter.poll()
        assert len(events) == 0

    def test_wrong_protocol_version_is_discarded(self) -> None:
        adapter, fake = _make_adapter_with_fake()
        msg = json.dumps({"v": 99, "type": "heartbeat", "event_id": "hb-bad"})
        fake.inject(msg + "\n")

        events = adapter.poll()
        assert len(events) == 0

    def test_missing_type_field_is_discarded(self) -> None:
        adapter, fake = _make_adapter_with_fake()
        msg = json.dumps({"v": 1, "event_id": "no-type"})
        fake.inject(msg + "\n")

        events = adapter.poll()
        assert len(events) == 0

    def test_json_array_is_discarded(self) -> None:
        adapter, fake = _make_adapter_with_fake()
        fake.inject("[1, 2, 3]\n")

        events = adapter.poll()
        assert len(events) == 0

    def test_empty_line_is_ignored(self) -> None:
        adapter, fake = _make_adapter_with_fake()
        fake.inject("\n\n\n")

        events = adapter.poll()
        assert len(events) == 0


class TestBufferSplitting:
    """Test line buffer accumulation and splitting."""

    def test_multiple_messages_in_one_read(self) -> None:
        adapter, fake = _make_adapter_with_fake()
        msg1 = json.dumps({"v": 1, "type": "heartbeat", "event_id": "hb-1"})
        msg2 = json.dumps({"v": 1, "type": "heartbeat", "event_id": "hb-2"})
        fake.inject(msg1 + "\n" + msg2 + "\n")

        events = adapter.poll()
        assert len(events) == 2
        assert events[0].event_id == "hb-1"
        assert events[1].event_id == "hb-2"

    def test_partial_message_buffered_across_polls(self) -> None:
        adapter, fake = _make_adapter_with_fake()
        full_msg = json.dumps({"v": 1, "type": "heartbeat", "event_id": "hb-split"})

        # Send first half
        half = len(full_msg) // 2
        fake.inject(full_msg[:half])
        events1 = adapter.poll()
        assert len(events1) == 0

        # Send second half + newline
        fake.inject(full_msg[half:] + "\n")
        events2 = adapter.poll()
        assert len(events2) == 1
        assert events2[0].event_id == "hb-split"

    def test_good_and_bad_messages_mixed(self) -> None:
        adapter, fake = _make_adapter_with_fake()
        good = json.dumps({"v": 1, "type": "heartbeat", "event_id": "good-1"})
        bad = "this is not json"
        fake.inject(good + "\n" + bad + "\n")

        events = adapter.poll()
        assert len(events) == 1
        assert events[0].event_id == "good-1"


class TestSendCommand:
    """Test access command serialization."""

    def test_send_access_command_formats_ndjson(self) -> None:
        from app.ports.device_transport import DeviceCommand

        adapter, fake = _make_adapter_with_fake()
        command = DeviceCommand(
            command_id="cmd-001",
            session_id="sess-001",
            decision="grant",
            reason="MATCHED_OWNER",
            door_hold_ms=3000,
        )

        adapter.send_access_command(command)
        output = fake.get_output()

        # Should be single NDJSON line
        assert output.endswith("\n")
        parsed = json.loads(output.strip())
        assert parsed["v"] == 1
        assert parsed["type"] == "access_command"
        assert parsed["command_id"] == "cmd-001"
        assert parsed["decision"] == "grant"
        assert parsed["door_hold_ms"] == 3000

    def test_send_command_raises_when_disconnected(self) -> None:
        import pytest

        from app.ports.device_transport import DeviceCommand

        adapter = Esp32SerialAdapter()
        command = DeviceCommand(
            command_id="cmd-fail",
            session_id="sess-fail",
            decision="deny",
            reason="TIMEOUT",
            door_hold_ms=0,
        )

        with pytest.raises(ConnectionError):
            adapter.send_access_command(command)


class TestConnectionState:
    """Test connection state management."""

    def test_is_connected_false_before_open(self) -> None:
        adapter = Esp32SerialAdapter()
        assert adapter.is_connected() is False

    def test_poll_returns_empty_when_disconnected(self) -> None:
        adapter = Esp32SerialAdapter()
        assert adapter.poll() == []

    def test_is_connected_true_with_fake(self) -> None:
        adapter, _ = _make_adapter_with_fake()
        assert adapter.is_connected() is True
