from __future__ import annotations

import unittest

from pc.communication.acceptance import run_offline_acceptance
from pc.communication.fake_plc import FakeAcceptancePlc
from pc.communication.s7 import PlcControls, unpack_state


class OfflineAcceptanceTests(unittest.TestCase):
    def test_all_offline_scenarios_pass(self) -> None:
        document = run_offline_acceptance()
        self.assertEqual(document["summary"]["scenario_count"], 5)
        self.assertTrue(document["summary"]["all_scenarios_pass"])

    def test_fake_plc_held_command_valid_is_single_shot(self) -> None:
        plc = FakeAcceptancePlc()
        plc.connect("fake", 0, 1)
        low = PlcControls(
            test_enable=True,
            command_data_valid=True,
            shape_code=2,
            semantic_id=202,
            command_valid=False,
        )
        high = PlcControls(
            test_enable=True,
            command_data_valid=True,
            shape_code=2,
            semantic_id=202,
            command_valid=True,
        )
        plc.db_write(12, 0, low.pack())
        for _ in range(3):
            plc.db_write(12, 0, high.pack())
        state = unpack_state(plc._status_bytes())
        self.assertEqual(state.queue_length, 1)
        self.assertFalse(state.queue_full)
        plc.disconnect()


if __name__ == "__main__":
    unittest.main()
