from __future__ import annotations

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "ubpet"
EVENT_VISIT = f"{DOMAIN}_visit"
DEFAULT_SCAN_INTERVAL = timedelta(minutes=3)

try:
    from .secrets import (
        APP_ID as DEFAULT_APP_ID,
        APP_KEY as DEFAULT_APP_KEY,
        BASE_URL as DEFAULT_BASE_URL,
        PRODUCT as DEFAULT_PRODUCT,
    )
except ImportError:
    DEFAULT_APP_ID = ""
    DEFAULT_APP_KEY = ""
    DEFAULT_BASE_URL = ""
    DEFAULT_PRODUCT = ""

try:
    from .secrets import US_APP_ID, US_APP_KEY
except ImportError:
    US_APP_ID = ""
    US_APP_KEY = ""

CONF_APP_KEY = "app_key"
CONF_APP_ID = "app_id"
CONF_AREA_CODE = "area_code"
CONF_COUNTRY = "country"
CONF_DEVICE_ID = "device_id"
CONF_BASE_URL = "base_url"
CONF_PRODUCT = "product"

EU_BASE_URL = "https://apis-eu.airrobo-home.com"
RUSSIA_BASE_URL = "https://apis-ru.airrobo-home.com"
US_BASE_URL = "https://apis.airrobo-home.com"

# The US AIR PET app (com.yibainetwork.airpet) has its own app id, which selects
# a separate user pool, so US accounts don't exist under the European app id.
US_COUNTRIES = ("US", "CA")

# Countries returned by the UPET 2.1.14 region map for the European app.
SUPPORTED_COUNTRIES = (
    "AL", "AD", "AT", "BY", "BH", "BE", "BA", "BG", "HR", "CY", "CZ",
    "DK", "EE", "FO", "FI", "FR", "GE", "DE", "GI", "GR", "HU", "IS",
    "IE", "IT", "KW", "XK", "LV", "LI", "LT", "LU", "MT", "MD", "MC",
    "ME", "NL", "MK", "NO", "PT", "PL", "QA", "RO", "RU", "SE", "CH",
    "SA", "SM", "RS", "SK", "SI", "ES", "TR", "UA", "GB", "AE", "VA",
) + US_COUNTRIES


def base_url_for_country(country: str) -> str:
    """Return the vendor API endpoint used by the mobile app for a country."""
    if country in US_COUNTRIES:
        return US_BASE_URL
    return RUSSIA_BASE_URL if country == "RU" else EU_BASE_URL


def app_credentials_for_country(country: str) -> tuple[str, str]:
    """Return the (app id, app key) of the mobile app sold in a country."""
    if country in US_COUNTRIES:
        return US_APP_ID, US_APP_KEY
    return DEFAULT_APP_ID, DEFAULT_APP_KEY


PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SWITCH,
    Platform.TIME,
    Platform.SELECT,
    Platform.BUTTON,
]
