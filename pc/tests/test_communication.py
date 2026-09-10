from __future__ import annotations

import unittest

from pc.communication.config import PlcCommunicationConfig
from pc.communication.models import command_from_event, label_to_shape_code
from pc.communication.sink import RecordingPlcSink, S7PlcCommandSink
from pc.communication.s7 import LAYOUT_MAGIC, LAYOUT_VERSION, PlcControls, unpack_state
from pc.events.models import EventType, VisionEvent


def _event(label: str, event_type: EventType = EventType.OBJECT_ENTER) -> VisionEvent:
    return VisionEvent(
        event_id=1,
        event_type=event_type,
        object_id=7,
        label=label,
        confidence=0.95,
        frame_index=10,
    )


def _status_raw(queue_length: int = 0) -> bytes:
    raw = bytearray(16)
    raw[0] = 0b00000001  # AcceptanceReady
    raw[1] = queue_length
    raw[8:12] = (123).to_bytes(4, "big", signed=False)
    raw[12:14] = LAYOUT_MAGIC.to_bytes(2, "big", signed=False)
    raw[14] = LAYOUT_VERSION
    return bytes(raw)


class FakeLowLevelClient:
    def __init__(self) -> None:
        self.connected = False
        self.writes: list[tuple[int, int, bytes]] = []

    def connect(self, host: str, rack: int, slot: int) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def get_connected(self) -> bool:
        return self.connected

    def db_read(self, db_number: int, offset: int, size: int) -> bytes:
        assert (db_number, offset, size) == (12, 8, 16)
        return _status_raw()

    def db_write(self, db_number: int, offset: int, raw: bytes) -> None:
        self.writes.append((db_number, offset, bytes(raw)))


class ShapeCommandTests(unittest.TestCase):
    def test_label_mapping(self) -> None:
        self.assertEqual(label_to_shape_code("triangle"), 1)
        self.assertEqual(label_to_shape_code("rectangle"), 2)
        self.assertEqual(label_to_shape_code("circle"), 3)
        self.assertIsNone(label_to_shape_code("unknown"))

    def test_event_filter(self) -> None:
        command = command_from_event(_event("circle"))
        self.assertIsNotNone(command)
        assert command is not None
        self.assertEqual(command.shape_code, 3)
        self.assertEqual(command.semantic_id, 7)
        self.assertIsNone(command_from_event(_event("circle", EventType.OBJECT_EXIT)))
        self.assertIsNone(command_from_event(_event("unknown")))


class ControlsTests(unittest.TestCase):
    def test_pack_matches_fixed_acceptance_layout(self) -> None:
        controls = PlcControls(
            test_enable=True,
            command_valid=True,
            command_data_valid=True,
            dequeue_request=True,
            reset_request=True,
            shape_code=3,
            semantic_id=103,
        )
        self.assertEqual(controls.pack(), b"\x1f\x03\x00\x00\x00\x00\x00g")

    def test_unpack_status(self) -> None:
        state = unpack_state(_status_raw(queue_length=2))
        self.assertTrue(state.acceptance_ready)
        self.assertEqual(state.queue_length, 2)
        self.assertEqual(state.layout_magic, LAYOUT_MAGIC)
        self.assertEqual(state.layout_version, LAYOUT_VERSION)


class SinkTests(unittest.TestCase):
    def test_recording_sink_filters_exit_and_unknown(self) -> None:
        sink = RecordingPlcSink()
        result = sink.send_event(_event("triangle"))
        self.assertEqual(result.status.value, "SENT")
        self.assertEqual([command.shape_code for command in sink.commands], [1])
        self.assertEqual(sink.send_event(_event("circle", EventType.OBJECT_EXIT)).status.value, "SKIPPED")
        self.assertEqual(sink.send_event(_event("unknown")).status.value, "SKIPPED")
        self.assertEqual(len(sink.commands), 1)

    def test_s7_sink_send_pulse_and_auto_dequeue(self) -> None:
        client = FakeLowLevelClient()
        config = PlcCommunicationConfig(
            enabled=True,
            db_number=12,
            auto_dequeue=False,
            command_pulse_seconds=0.0,
            dequeue_pulse_seconds=0.0,
            reset_pulse_seconds=0.0,
        )
        sink = S7PlcCommandSink(config, low_level=client)
        sink.start()
        result = sink.send_event(_event("rectangle"))
        sink.stop()

        self.assertEqual(result.status.value, "SENT")
        self.assertEqual(result.queue_length, 0)
        self.assertEqual(len(client.writes), 4)  # low, high, low, final safe controls
        self.assertEqual(client.writes[0][1], 0)
        self.assertEqual(client.writes[1][2][0] & 0b00000010, 0b00000010)
        self.assertFalse(client.connected)

    def test_config_requires_db_number_when_enabled(self) -> None:
        with self.assertRaises(ValueError):
            PlcCommunicationConfig(enabled=True, db_number=None).validate()


if __name__ == "__main__":
    unittest.main()
