from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


CONST_PATH = Path(__file__).resolve().parents[1] / "custom_components" / "ubpet" / "const.py"


class _Platform:
    SENSOR = "sensor"
    BINARY_SENSOR = "binary_sensor"
    NUMBER = "number"
    SWITCH = "switch"
    TIME = "time"
    SELECT = "select"
    BUTTON = "button"


def _load_const_module():
    homeassistant_module = types.ModuleType("homeassistant")
    homeassistant_const_module = types.ModuleType("homeassistant.const")
    homeassistant_const_module.Platform = _Platform
    spec = importlib.util.spec_from_file_location("ubpet_const_test", CONST_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    with patch.dict(
        sys.modules,
        {
            "homeassistant": homeassistant_module,
            "homeassistant.const": homeassistant_const_module,
        },
    ):
        spec.loader.exec_module(module)
    return module


class ConstUnitTests(unittest.TestCase):
    def test_russia_uses_dedicated_api_endpoint(self):
        const = _load_const_module()

        self.assertEqual(const.base_url_for_country("RU"), const.RUSSIA_BASE_URL)

    def test_other_supported_countries_use_eu_api_endpoint(self):
        const = _load_const_module()

        self.assertEqual(const.base_url_for_country("UA"), const.EU_BASE_URL)
        self.assertEqual(const.base_url_for_country("DE"), const.EU_BASE_URL)

    def test_us_and_canada_use_us_api_endpoint(self):
        const = _load_const_module()

        self.assertEqual(const.base_url_for_country("US"), const.US_BASE_URL)
        self.assertEqual(const.base_url_for_country("CA"), const.US_BASE_URL)

    def test_us_accounts_use_air_pet_app_credentials(self):
        const = _load_const_module()

        self.assertEqual(const.app_credentials_for_country("US"), (const.US_APP_ID, const.US_APP_KEY))
        self.assertEqual(const.app_credentials_for_country("DE"), (const.DEFAULT_APP_ID, const.DEFAULT_APP_KEY))
