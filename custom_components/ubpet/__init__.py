from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant

from .api import UbpetClient
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
    DEFAULT_BASE_URL,
    DEFAULT_PRODUCT,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import UbpetDataUpdateCoordinator
from .push import UbpetPush

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    app_key = entry.data.get(CONF_APP_KEY, DEFAULT_APP_KEY)
    app_id = entry.data.get(CONF_APP_ID, DEFAULT_APP_ID)
    base_url = entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL)
    product = entry.data.get(CONF_PRODUCT, DEFAULT_PRODUCT)
    missing = [
        field
        for field, value in (
            (CONF_APP_KEY, app_key),
            (CONF_APP_ID, app_id),
            (CONF_BASE_URL, base_url),
            (CONF_PRODUCT, product),
        )
        if not value
    ]
    if missing:
        _LOGGER.error("UPET setup has missing API field(s): %s", ", ".join(missing))

    client = UbpetClient(
        account=entry.data["account"],
        password=entry.data["password"],
        app_key=app_key,
        device_id=entry.data[CONF_DEVICE_ID],
        app_id=app_id,
        base_url=base_url,
        product=product,
        area_code=entry.data.get(CONF_AREA_CODE, entry.data.get(CONF_COUNTRY, "")),
    )
    coordinator = UbpetDataUpdateCoordinator(hass, client, entry_id=entry.entry_id)
    await coordinator.async_config_entry_first_refresh()

    coordinator.push = UbpetPush(hass, coordinator)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_create_background_task(hass, coordinator.push.async_start(), "ubpet mqtt push")

    async def _stop_push(_event) -> None:
        await coordinator.push.async_stop()

    entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _stop_push))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id, None)
        if coordinator is not None:
            await coordinator.push.async_stop()
    return unload_ok
