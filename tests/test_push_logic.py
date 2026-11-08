from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

PATH = Path(__file__).resolve().parents[1] / "custom_components" / "ubpet" / "push_logic.py"
spec = importlib.util.spec_from_file_location("ubpet_push_logic_test", PATH)
push_logic = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = push_logic
spec.loader.exec_module(push_logic)


class ReconnectDelayTests(unittest.TestCase):
    def test_first_failure_waits_a_minute(self):
        self.assertEqual(push_logic.reconnect_delay(0, session_s=5, own_login=False), 60)

    def test_repeated_short_sessions_double_up_to_thirty_minutes(self):
        delays = [0]
        for _ in range(7):
            delays.append(push_logic.reconnect_delay(delays[-1], session_s=5, own_login=False))
        self.assertEqual(delays[1:], [60, 120, 240, 480, 960, 1800, 1800])

    def test_stable_session_resets_backoff(self):
        self.assertEqual(push_logic.reconnect_delay(1800, session_s=600, own_login=False), 60)

    def test_own_login_reconnects_quickly(self):
        self.assertEqual(push_logic.reconnect_delay(1800, session_s=5, own_login=True), 5)


class CatLeftTests(unittest.TestCase):
    def test_cat_leaving_is_detected(self):
        self.assertTrue(push_logic.cat_left({"toilet_state": 1}, {"w_state": 1}))

    def test_other_transitions_are_not(self):
        self.assertFalse(push_logic.cat_left(None, {"w_state": 1}))
        self.assertFalse(push_logic.cat_left({"w_state": 1}, {"toilet_state": 1}))
        self.assertFalse(push_logic.cat_left({"toilet_state": 1}, {"toilet_state": 1}))


if __name__ == "__main__":
    unittest.main()
