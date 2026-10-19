from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

PATH = Path(__file__).resolve().parents[1] / "custom_components" / "ubpet" / "registry.py"
spec = importlib.util.spec_from_file_location("ubpet_registry_test", PATH)
registry = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = registry
spec.loader.exec_module(registry)

DATA = {"devices": {"SN1": {}}, "cats": [{"catInfoId": 529029}]}


class StillReportedTests(unittest.TestCase):
    def test_current_box_and_cat_are_reported(self):
        self.assertTrue(registry.still_reported({("ubpet", "SN1")}, DATA))
        self.assertTrue(registry.still_reported({("ubpet", "cat_529029")}, DATA))

    def test_cat_from_before_a_re_pair_is_not(self):
        self.assertFalse(registry.still_reported({("ubpet", "cat_156382")}, DATA))

    def test_other_domains_are_ignored(self):
        self.assertFalse(registry.still_reported({("other", "SN1")}, DATA))


if __name__ == "__main__":
    unittest.main()
