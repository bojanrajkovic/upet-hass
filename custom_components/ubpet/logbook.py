from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.core import Event, HomeAssistant, callback

from .const import DOMAIN, EVENT_VISIT


@callback
def async_describe_events(
    hass: HomeAssistant,
    async_describe_event: Callable[[str, str, Callable[[Event], dict[str, Any]]], None],
) -> None:
    @callback
    def describe_visit(event: Event) -> dict[str, Any]:
        data = event.data
        return {
            "name": data.get("cat") or "Unidentified cat",
            "message": f"used {data.get('box') or 'the litter box'} ({data.get('weight_kg')} kg, {data.get('duration_s')} s)",
        }

    async_describe_event(DOMAIN, EVENT_VISIT, describe_visit)
