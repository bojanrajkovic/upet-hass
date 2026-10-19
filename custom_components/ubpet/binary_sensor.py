from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity, BinarySensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import UbpetDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class UbpetBinarySensorDescription(BinarySensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]
    attrs_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


# What the app tells the owner for each motor_state when the drum is stuck.
DRUM_STUCK_POSITIONS = {
    1: "There may be clumps at the start position",
    2: "There may be clumps in the litter bin",
    3: "There may be clumps in the rotation section of the litter bin",
    4: "There may be clumps causing blockage in the waste bin",
}


def _state(item: dict[str, Any], field: str) -> int | None:
    """A field of the box's latest state push; absent means 0, None until the first push."""
    state = item.get("mqtt_state")
    return state.get(field, 0) if isinstance(state, dict) else None


def _state_is(field: str, test: Callable[[int], bool]) -> Callable[[dict[str, Any]], bool | None]:
    def value(item: dict[str, Any]) -> bool | None:
        current = _state(item, field)
        return None if current is None else test(current)

    return value


BINARY_SENSORS: tuple[UbpetBinarySensorDescription, ...] = (
    UbpetBinarySensorDescription(
        key="cat_nearby",
        name="Cat nearby",
        icon="mdi:cat",
        translation_key="cat_nearby",
        device_class=BinarySensorDeviceClass.OCCUPANCY,
        value_fn=_state_is("foreign_state", lambda value: value == 1),
    ),
    UbpetBinarySensorDescription(
        key="back_cover_open",
        name="Back cover open",
        translation_key="back_cover_open",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=_state_is("lid_state", lambda value: value == 1),
    ),
    UbpetBinarySensorDescription(
        key="drum_not_in_place",
        name="Drum not in place",
        translation_key="drum_not_in_place",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=_state_is("box_state", lambda value: value == 1),
    ),
    UbpetBinarySensorDescription(
        key="drum_stuck",
        name="Drum stuck",
        translation_key="drum_stuck",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=_state_is("motor_state", lambda value: value in DRUM_STUCK_POSITIONS),
        attrs_fn=lambda item: {"likely_cause": DRUM_STUCK_POSITIONS.get(_state(item, "motor_state"))},
    ),
    UbpetBinarySensorDescription(
        key="scale_fault",
        name="Scale fault",
        translation_key="scale_fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_state_is("weigh_sensor", lambda value: value == 1),
    ),
    UbpetBinarySensorDescription(
        key="camera_fault",
        name="Camera fault",
        translation_key="camera_fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_state_is("camera_state", lambda value: value == 1),
    ),
    UbpetBinarySensorDescription(
        key="light",
        name="Light",
        translation_key="light",
        device_class=BinarySensorDeviceClass.LIGHT,
        value_fn=_state_is("led_state", lambda value: value > 0),
    ),
    UbpetBinarySensorDescription(
        key="firmware_updating",
        name="Firmware updating",
        translation_key="firmware_updating",
        device_class=BinarySensorDeviceClass.UPDATE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_state_is("update_state", lambda value: value == 1),
    ),
    UbpetBinarySensorDescription(
        key="cat_inside",
        name="Cat inside",
        icon="mdi:cat",
        translation_key="cat_inside",
        device_class=BinarySensorDeviceClass.OCCUPANCY,
        value_fn=lambda item: _cat_inside(item),
    ),
    UbpetBinarySensorDescription(
        key="online",
        name="Online",
        icon="mdi:wifi",
        translation_key="online",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda item: item["online"].get("online"),
    ),
    UbpetBinarySensorDescription(
        key="deodorant_expired",
        name="Deodorant expired",
        icon="mdi:air-filter",
        translation_key="deodorant_expired",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda item: item["deodorant"].get("expired"),
    ),
    UbpetBinarySensorDescription(
        key="sensor_switch",
        name="Sensor enabled",
        icon="mdi:motion-sensor",
        translation_key="sensor_switch",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda item: item["config"].get("sensorSwitch") == 1,
    ),
    UbpetBinarySensorDescription(
        key="camera_switch",
        name="Camera enabled",
        icon="mdi:camera",
        translation_key="camera_switch",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda item: item["config"].get("cameraSwitch") == 1,
    ),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: UbpetDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        UbpetDeviceBinarySensor(coordinator, entry.entry_id, serial, description)
        for serial in coordinator.data.get("devices", {})
        for description in BINARY_SENSORS
    ]
    async_add_entities(entities)


class UbpetDeviceBinarySensor(CoordinatorEntity[UbpetDataUpdateCoordinator], BinarySensorEntity):
    entity_description: UbpetBinarySensorDescription

    def __init__(self, coordinator: UbpetDataUpdateCoordinator, entry_id: str, serial: str, description: UbpetBinarySensorDescription) -> None:
        super().__init__(coordinator)
        self._serial = serial
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{serial}_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        item = self.coordinator.data.get("devices", {}).get(self._serial, {})
        device = item.get("device", {})
        return DeviceInfo(
            identifiers={(DOMAIN, self._serial)},
            manufacturer="Airrobo / UBT",
            name=device.get("deviceName") or self._serial,
            serial_number=self._serial,
        )

    @property
    def is_on(self) -> bool | None:
        item = self.coordinator.data.get("devices", {}).get(self._serial)
        if not item:
            return None
        value = self.entity_description.value_fn(item)
        return None if value is None else bool(value)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        item = self.coordinator.data.get("devices", {}).get(self._serial)
        if not item or self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(item)


def _cat_inside(item: dict[str, Any]) -> bool | None:
    # The box reports toilet_state=1 while a cat is on the scale and drops the field once it leaves.
    state = item.get("mqtt_state")
    return state.get("toilet_state") == 1 if isinstance(state, dict) else None
