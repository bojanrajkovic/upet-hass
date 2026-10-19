from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
import logging
import time
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import UbpetApiError, UbpetClient
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, EVENT_VISIT
from .mqtt import RISP_CMD_ALL_STATE_RESPONSE, RISP_CMD_STATE_PUSH
from .visits import new_visits, visit_event_data

if TYPE_CHECKING:
    from .push import UbpetPush

_LOGGER = logging.getLogger(__name__)



class UbpetDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(
        self,
        hass: HomeAssistant,
        client: UbpetClient,
        *,
        entry_id: str,
        update_interval: timedelta = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
            always_update=True,
        )
        self.client = client
        # Set by async_setup_entry before the platforms load.
        self.push: UbpetPush
        self._mqtt_state_by_serial: dict[str, dict[str, Any]] = {}
        self._last_rest_update_at: datetime | None = None
        self._last_mqtt_update_at_by_serial: dict[str, datetime] = {}
        # Last reported cat record id per serial. Stored so a restart neither drops nor replays visits.
        self._visit_store: Store[dict[str, int]] = Store(hass, 1, f"{DOMAIN}.{entry_id}.visits")
        self._visit_cursor: dict[str, int] | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        started = time.monotonic()
        _LOGGER.info("Starting UPET data update")
        try:
            data = await self.hass.async_add_executor_job(self.client.get_dashboard)
        except (OSError, RuntimeError, UbpetApiError) as err:
            _LOGGER.exception("UPET data update failed")
            raise UpdateFailed(str(err)) from err

        devices = data.get("devices", {})
        cats = data.get("cats", [])
        _LOGGER.info(
            "Finished UPET data update in %.2fs: devices=%s cats=%s",
            time.monotonic() - started,
            len(devices) if isinstance(devices, dict) else 0,
            len(cats) if isinstance(cats, list) else 0,
        )
        self._last_rest_update_at = datetime.now(UTC)
        if isinstance(devices, dict):
            await self._fire_new_visits(devices)
        data = self._with_runtime_state(data)
        return data

    async def _fire_new_visits(self, devices: dict[str, Any]) -> None:
        if self._visit_cursor is None:
            self._visit_cursor = await self._visit_store.async_load() or {}
        changed = False
        for serial, item in devices.items():
            batch = new_visits(item.get("cat_records") or [], self._visit_cursor.get(serial))
            box_name = item.get("device", {}).get("deviceName")
            for record in batch.visits:
                self.hass.bus.async_fire(EVENT_VISIT, visit_event_data(serial, box_name, record))
            if batch.last_record_id is not None and batch.last_record_id != self._visit_cursor.get(serial):
                self._visit_cursor[serial] = batch.last_record_id
                changed = True
            if batch.visits:
                _LOGGER.info("UPET reported %s new visit(s) for %s", len(batch.visits), serial)
        if changed:
            await self._visit_store.async_save(self._visit_cursor)

    def store_mqtt_result(self, serial: str, result: dict[str, Any] | object) -> bool:
        state = _latest_mqtt_state(result)
        if state is None:
            return False
        self._mqtt_state_by_serial[serial] = state
        self._last_mqtt_update_at_by_serial[serial] = datetime.now(UTC)
        self._update_runtime_data()
        return True

    def mqtt_state(self, serial: str) -> dict[str, Any] | None:
        return self._mqtt_state_by_serial.get(serial)

    def set_online(self, serial: str, online: bool) -> None:
        """Apply an online/offline push; the next REST refresh reports the same value."""
        item = (self.data or {}).get("devices", {}).get(serial)
        if isinstance(item, dict) and isinstance(item.get("online"), dict):
            item["online"]["online"] = online
            self.async_update_listeners()

    @property
    def last_rest_update_at(self) -> datetime | None:
        return self._last_rest_update_at

    def last_mqtt_update_at(self, serial: str) -> datetime | None:
        return self._last_mqtt_update_at_by_serial.get(serial)

    def set_mqtt_work_state(self, serial: str, state: dict[str, Any]) -> None:
        mqtt_state = deepcopy(self._mqtt_state_by_serial.get(serial, {}))
        mqtt_state.update(state)
        mqtt_state["optimistic"] = True
        mqtt_state["optimistic_updated_at"] = time.time()
        self._mqtt_state_by_serial[serial] = mqtt_state
        self._update_runtime_data()

    def _update_runtime_data(self) -> None:
        self.data = self._with_runtime_state(self.data or {})
        self.async_update_listeners()

    def _with_runtime_state(self, data: dict[str, Any]) -> dict[str, Any]:
        if (
            not self._mqtt_state_by_serial
            and self._last_rest_update_at is None
            and not self._last_mqtt_update_at_by_serial
        ):
            return data
        merged = deepcopy(data)
        devices = merged.get("devices")
        if not isinstance(devices, dict):
            return merged
        for serial, item in devices.items():
            if not isinstance(item, dict):
                continue
            if state := self._mqtt_state_by_serial.get(serial):
                item["mqtt_state"] = deepcopy(state)
            item["runtime_state"] = {
                "last_rest_update_at": self._last_rest_update_at,
                "last_mqtt_update_at": self._last_mqtt_update_at_by_serial.get(serial),
            }
        return merged

def _latest_mqtt_state(result: dict[str, Any] | object) -> dict[str, Any] | None:
    if not isinstance(result, dict):
        return None
    messages = result.get("received_messages")
    if not isinstance(messages, list):
        return None

    latest: dict[str, Any] | None = None
    for message in messages:
        if not isinstance(message, dict):
            continue
        decoded = message.get("decoded")
        if not isinstance(decoded, dict):
            continue
        if decoded.get("risp_cmd") not in (RISP_CMD_ALL_STATE_RESPONSE, RISP_CMD_STATE_PUSH):
            continue
        if "w_mode_app_name" not in decoded and "w_state_app_name" not in decoded:
            continue
        latest = {
            "cid": decoded.get("cid"),
            "from_uid": decoded.get("from_uid"),
            "to_uid": decoded.get("to_uid"),
            "received_phase": message.get("phase"),
            "received_topic": message.get("topic"),
            "received_qos": message.get("qos"),
            "mqtt_service": result.get("service_id"),
            "command_cid": result.get("cid"),
            "command_gid": result.get("gid"),
            "command_created_at_ms": result.get("created_at_ms"),
        }
        for key, value in decoded.items():
            if key in {
                "payload_hex",
                "raw_hex",
            }:
                continue
            if value not in (None, ""):
                latest[key] = value
    return latest
