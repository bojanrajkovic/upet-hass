from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

VISITS_PATH = Path(__file__).resolve().parents[1] / "custom_components" / "ubpet" / "visits.py"
spec = importlib.util.spec_from_file_location("ubpet_visits_test", VISITS_PATH)
visits = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = visits
spec.loader.exec_module(visits)


def _record(record_id: int, **overrides):
    return {
        "recordId": record_id,
        "eventTime": 1792356940000,
        "eventType": 3,
        "catInfoId": 156392,
        "catNickname": "Hilda",
        "weight": 3.3,
        "costTime": 59,
        **overrides,
    }


class NewVisitsTests(unittest.TestCase):
    def test_first_poll_seeds_cursor_without_visits(self):
        decision = visits.new_visits([_record(3), _record(2)], last_record_id=None)

        self.assertEqual(decision, visits.VisitBatch(visits=[], last_record_id=3))

    def test_returns_only_newer_records_oldest_first(self):
        # The API returns newest first.
        decision = visits.new_visits([_record(5), _record(4), _record(3)], last_record_id=3)

        self.assertEqual([r["recordId"] for r in decision.visits], [4, 5])
        self.assertEqual(decision.last_record_id, 5)

    def test_no_records_keeps_cursor(self):
        decision = visits.new_visits([], last_record_id=7)

        self.assertEqual(decision, visits.VisitBatch(visits=[], last_record_id=7))


class VisitEventDataTests(unittest.TestCase):
    def test_identified_cat(self):
        data = visits.visit_event_data("SN1", "Left Litter Box", _record(9))

        self.assertEqual(
            data,
            {
                "serial_number": "SN1",
                "box": "Left Litter Box",
                "record_id": 9,
                "cat_id": 156392,
                "cat": "Hilda",
                "weight_kg": 3.3,
                "duration_s": 59,
                "event_type": 3,
                "time": "2026-10-18T20:55:40+00:00",
            },
        )

    def test_unidentified_cat_has_no_cat_id(self):
        data = visits.visit_event_data("SN1", "Right", _record(9, eventType=21, catInfoId=0, catNickname=None))

        self.assertIsNone(data["cat_id"])
        self.assertIsNone(data["cat"])


if __name__ == "__main__":
    unittest.main()
