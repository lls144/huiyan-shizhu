import importlib.util
import sys
from pathlib import Path

import pytest


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


class _ConfirmingSnap7:
    """Fake transport whose DB silently drops the first ``drop`` control writes."""

    def __init__(self, drop: int = 0) -> None:
        self.control = bytes(MODULE.CONTROL_SIZE)
        self.writes: list[tuple[int, int, bytes]] = []
        self.drop = drop

    def db_write(self, db_number, offset, raw):
        self.writes.append((db_number, offset, bytes(raw)))
        if self.drop > 0:
            self.drop -= 1
            return
        self.control = bytes(raw)

    def db_read(self, db_number, offset, size):
        assert (db_number, offset, size) == (12, 0, MODULE.CONTROL_SIZE)
        return self.control


def test_control_write_is_limited_to_first_eight_bytes():
    fake = _ConfirmingSnap7()
    client = MODULE.S7AcceptanceClient("127.0.0.1", 0, 1, 12, write_confirm_interval=0.0)
    client.client = fake
    client.write_controls(
        test_enable=True,
        command_valid=True,
        command_data_valid=True,
        dequeue_request=True,
        reset_request=True,
        shape_code=3,
        semantic_id=103,
    )
    assert fake.writes == [(12, 0, b"\x1f\x03\x00\x00\x00\x00\x00g")]
    assert client.write_log == [1]


def test_control_write_is_confirmed_by_readback():
    fake = _ConfirmingSnap7()
    client = MODULE.S7AcceptanceClient("127.0.0.1", 0, 1, 12, write_confirm_interval=0.0)
    client.client = fake

    client.write_controls(test_enable=True, shape_code=2, semantic_id=102)

    assert fake.control == client.pack_controls()
    assert client.read_controls() == client.pack_controls()
    assert client.write_stats() == {
        "confirmed_control_writes": 1,
        "writes_needing_retry": 0,
        "max_attempts": 1,
    }


def test_control_write_is_re_sent_while_the_plc_drops_it():
    fake = _ConfirmingSnap7(drop=2)
    client = MODULE.S7AcceptanceClient("127.0.0.1", 0, 1, 12, write_confirm_interval=0.0)
    client.client = fake

    client.write_controls(test_enable=True)

    assert len(fake.writes) == 3
    assert fake.writes[0] == fake.writes[1] == fake.writes[2]
    assert client.write_log == [3]
    assert client.write_stats()["writes_needing_retry"] == 1


def test_control_write_raises_when_the_plc_never_takes_it():
    fake = _ConfirmingSnap7(drop=99)
    client = MODULE.S7AcceptanceClient(
        "127.0.0.1", 0, 1, 12, write_confirm_attempts=3, write_confirm_interval=0.0
    )
    client.client = fake

    with pytest.raises(MODULE.AcceptanceError):
        client.write_controls(test_enable=True)

    assert len(fake.writes) == 3
    assert client.write_log == [3]


def test_restore_safe_controls_clears_all_python_owned_fields():
    fake = _ConfirmingSnap7()
    client = MODULE.S7AcceptanceClient("127.0.0.1", 0, 1, 12)
    client.client = fake
    client.write_controls(test_enable=True, command_valid=True, shape_code=3, semantic_id=103)
    client.restore_safe_controls()
    assert fake.writes[-1][2] == bytes(MODULE.CONTROL_SIZE)


def test_order_code_read_reports_a_real_mlfb():
    class FakeInfo:
        OrderCode = b"6ES7 214-1AG40-0XB0 "
        V1, V2, V3 = 4, 5, 1

    class FakeSnap7:
        def get_order_code(self):
            return FakeInfo()

    text = MODULE.cpu_order_code(FakeSnap7())
    assert "6ES7 214-1AG40-0XB0" in text
    assert "4.5.1" in text
    assert "UNRELIABLE" not in text


def test_order_code_read_flags_the_offset_bug_of_the_pinned_client():
    class FakeInfo:
        OrderCode = b""
        V1, V2, V3 = 45, 48, 88  # python-snap7 3.1.2 reports '-' '0' 'X'

    class FakeSnap7:
        def get_order_code(self):
            return FakeInfo()

    assert "UNRELIABLE" in MODULE.cpu_order_code(FakeSnap7())
