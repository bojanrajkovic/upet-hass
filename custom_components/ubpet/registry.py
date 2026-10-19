"""Pure device-registry decisions, free of Home Assistant imports so tests can load them."""

from __future__ import annotations

from typing import Any

DOMAIN = "ubpet"


def still_reported(identifiers: set[tuple[str, str]], data: dict[str, Any]) -> bool:
    """True if the vendor account still reports this box or cat.

    Boxes are identified by serial number and cats by `cat_<catInfoId>`. Re-pairing a box
    or recreating a cat profile gives it a new id, leaving the old device behind.
    """
    current = set(data.get("devices", {})) | {f"cat_{cat.get('catInfoId')}" for cat in data.get("cats", [])}
    return any(domain == DOMAIN and value in current for domain, value in identifiers)


def has_camera(item: dict[str, Any]) -> bool:
    """True unless the box's capabilities say it has no camera.

    The app treats the `cat_face_upload` capability as the camera-backed cat recognition
    feature. Capabilities that failed to load count as a camera, so an outage never hides
    entities on a box that has one.
    """
    capabilities = item.get("capabilities")
    if not isinstance(capabilities, dict):
        return True
    return any(c.get("code") == "cat_face_upload" for c in capabilities.get("capabilities") or [] if isinstance(c, dict))


def waste_bin_reminder_config(config: dict[str, Any]) -> dict[str, Any] | None:
    """The empty-waste-bin reminder's config, if the box has one set up.

    Boxes without the reminder still list a type-4 entry, but with no notifyConfigId.
    """
    for item in config.get("notifyConfigList") or []:
        if isinstance(item, dict) and item.get("type") == 4 and item.get("notifyConfigId") is not None:
            return item
    return None
