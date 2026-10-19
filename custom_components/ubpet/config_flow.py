from __future__ import annotations

from typing import Any
import uuid

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .api import UbpetApiError, UbpetClient
from .const import (
    CONF_AREA_CODE,
    CONF_APP_ID,
    CONF_APP_KEY,
    CONF_BASE_URL,
    CONF_COUNTRY,
    CONF_DEVICE_ID,
    CONF_PRODUCT,
    DEFAULT_APP_ID,
    DEFAULT_APP_KEY,
    DEFAULT_PRODUCT,
    DOMAIN,
    SUPPORTED_COUNTRIES,
    app_credentials_for_country,
    base_url_for_country,
)


def _schema(
    defaults: dict[str, Any] | None = None,
    *,
    default_country: str | None = None,
) -> vol.Schema:
    defaults = defaults or {}
    selected_country = defaults.get(CONF_COUNTRY, default_country)
    if isinstance(selected_country, str):
        selected_country = selected_country.upper()
    if selected_country not in SUPPORTED_COUNTRIES:
        selected_country = None
    country_field = (
        vol.Required(CONF_COUNTRY, default=selected_country)
        if selected_country
        else vol.Required(CONF_COUNTRY)
    )
    fields: dict[Any, Any] = {
        country_field: selector.CountrySelector(
            selector.CountrySelectorConfig(countries=list(SUPPORTED_COUNTRIES))
        ),
        vol.Required(CONF_USERNAME, default=defaults.get(CONF_USERNAME, "")): str,
        vol.Required(CONF_PASSWORD): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        ),
    }
    if not DEFAULT_APP_KEY:
        fields[vol.Required(CONF_APP_KEY, default=defaults.get(CONF_APP_KEY, ""))] = selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        )
    if not DEFAULT_APP_ID:
        fields[vol.Required(CONF_APP_ID, default=defaults.get(CONF_APP_ID, ""))] = str
    if not DEFAULT_PRODUCT:
        fields[vol.Required(CONF_PRODUCT, default=defaults.get(CONF_PRODUCT, ""))] = str
    return vol.Schema(fields)


def _validate_input(data: dict[str, Any]) -> list[dict[str, Any]]:
    account = _clean_required_string(data.get(CONF_USERNAME))
    password = _clean_required_string(data.get(CONF_PASSWORD))
    app_key = _clean_required_string(data.get(CONF_APP_KEY))
    app_id = _clean_required_string(data.get(CONF_APP_ID))
    base_url = _clean_required_string(data.get(CONF_BASE_URL))
    product = _clean_required_string(data.get(CONF_PRODUCT))
    client = UbpetClient(
        account=account,
        password=password,
        app_key=app_key,
        device_id=data.get(CONF_DEVICE_ID, uuid.uuid4().hex),
        app_id=app_id,
        base_url=base_url,
        product=product,
        area_code=_clean_optional_string(data.get(CONF_AREA_CODE)),
    )
    client.login()
    return client.get_devices()


def _clean_required_string(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("required value is empty")
    return value.strip()


def _clean_optional_string(value: Any) -> str:
    return value.strip().upper() if isinstance(value, str) else ""


def _clean_country(value: Any) -> str:
    country = _clean_optional_string(value)
    if country not in SUPPORTED_COUNTRIES:
        raise ValueError("unsupported country")
    return country


class UbpetConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                country = _clean_country(user_input.get(CONF_COUNTRY))
                app_id, app_key = app_credentials_for_country(country)
                connection_data = {
                    **user_input,
                    CONF_COUNTRY: country,
                    CONF_APP_KEY: app_key or user_input.get(CONF_APP_KEY),
                    CONF_APP_ID: app_id or user_input.get(CONF_APP_ID),
                    CONF_AREA_CODE: country,
                    CONF_BASE_URL: base_url_for_country(country),
                    CONF_PRODUCT: DEFAULT_PRODUCT or user_input.get(CONF_PRODUCT),
                    CONF_DEVICE_ID: uuid.uuid4().hex,
                }
                devices = await self.hass.async_add_executor_job(_validate_input, connection_data)
            except ValueError:
                errors["base"] = "missing_required"
            except UbpetApiError:
                errors["base"] = "auth_failed"
            except OSError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                app_id = _clean_required_string(connection_data[CONF_APP_ID])
                await self.async_set_unique_id(f"{app_id}:{user_input[CONF_USERNAME]}")
                self._abort_if_unique_id_configured()
                title = "UPET"
                if devices:
                    title = devices[0].get("deviceName") or devices[0].get("serialNumber") or title
                return self.async_create_entry(
                    title=title,
                    data={
                        "account": _clean_required_string(user_input[CONF_USERNAME]),
                        "password": _clean_required_string(user_input[CONF_PASSWORD]),
                        CONF_COUNTRY: country,
                        CONF_APP_KEY: _clean_required_string(connection_data[CONF_APP_KEY]),
                        CONF_AREA_CODE: country,
                        CONF_DEVICE_ID: connection_data[CONF_DEVICE_ID],
                        CONF_APP_ID: app_id,
                        CONF_BASE_URL: _clean_required_string(connection_data[CONF_BASE_URL]),
                        CONF_PRODUCT: _clean_required_string(connection_data[CONF_PRODUCT]),
                    },
                )

        configured_country = getattr(getattr(self.hass, "config", None), "country", None)
        return self.async_show_form(
            step_id="user",
            data_schema=_schema(user_input, default_country=configured_country),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return UbpetOptionsFlow(config_entry)


class UbpetOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        return self.async_create_entry(title="", data={})
