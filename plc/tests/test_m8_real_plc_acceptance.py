import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "tools" / "m8_real_plc_acceptance.py"
SPEC = importlib.util.spec_from_file_location("m8_acceptance", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
# `m8_real_plc_acceptance.py` uses `from __future__ import annotations` and
# defines dataclasses, so it must be registered in `sys.modules` before the
# module body runs; otherwise dataclasses cannot resolve string annotations.
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_parse_status_layout():
    raw = bytearray(16)
    raw[0] = 0b01111101
    raw[1] = 3
    raw[2] = 2
    raw[4:8] = (102).to_bytes(4, "big", signed=True)
    raw[8:12] = (1234).to_bytes(4, "big", signed=False)
    raw[12:14] = MODULE.LAYOUT_MAGIC.to_bytes(2, "big")
    raw[14] = MODULE.LAYOUT_VERSION

    class FakeSnap7:
        def db_read(self, db_number, offset, size):
            assert (db_number, offset, size) == (12, 8, 16)
            return raw

    client = MODULE.S7AcceptanceClient("127.0.0.1", 0, 1, 12)
    client.client = FakeSnap7()
    state = client.read_state()
    assert state.acceptance_ready
    assert not state.queue_empty
    assert state.queue_full
    assert state.leds == (True, True, True)
    assert state.last_dequeued_valid
    assert state.queue_length == 3
    assert state.last_dequeued_shape == 2
    assert state.last_dequeued_semantic_id == 102
    assert state.cycle_counter == 1234
    assert state.layout_magic == MODULE.LAYOUT_MAGIC
    assert state.layout_version == MODULE.LAYOUT_VERSION


def test_control_write_is_limited_to_first_eight_bytes():
    writes = []

    class FakeSnap7:
        def db_write(self, db_number, offset, raw):
            writes.append((db_number, offset, bytes(raw)))

    client = MODULE.S7AcceptanceClient("127.0.0.1", 0, 1, 12)
    client.client = FakeSnap7()
    client.write_controls(
        test_enable=True,
        command_valid=True,
        command_data_valid=True,
        dequeue_request=True,
        reset_request=True,
        shape_code=3,
        semantic_id=103,
    )
    assert writes == [(12, 0, b"\x1f\x03\x00\x00\x00\x00\x00g")]


def test_restore_safe_controls_clears_all_python_owned_fields():
    writes = []

    class FakeSnap7:
        def db_write(self, db_number, offset, raw):
            writes.append(bytes(raw))

    client = MODULE.S7AcceptanceClient("127.0.0.1", 0, 1, 12)
    client.client = FakeSnap7()
    client.write_controls(test_enable=True, command_valid=True, shape_code=3, semantic_id=103)
    client.restore_safe_controls()
    assert writes[-1] == bytes(8)
