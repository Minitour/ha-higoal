"""Diagnostics support for HIGOAL."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntry

from .client.manager import UnknownDevice
from .const import DOMAIN
from .data import HigoalConfigEntry

REDACT_CONFIG = {"username", "password"}
REDACT_DEVICE = {"home_id", "room_id", "mac", "ssid"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: HigoalConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    manager = entry.runtime_data.manager
    return {
        "config_entry": async_redact_data(dict(entry.data), REDACT_CONFIG),
        "mq_connected": manager.mq is not None and manager.mq.connected,
        "offline_devices": list(manager.offline_devices.keys()),
        "devices": [
            _device_as_dict(hass, device)
            for device in manager.device_map.values()
            if device is not UnknownDevice
        ],
    }


async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: HigoalConfigEntry, device: DeviceEntry
) -> dict[str, Any]:
    """Return diagnostics for a device entry."""
    manager = entry.runtime_data.manager

    higoal_device_id = next(
        identifier[1]
        for identifier in device.identifiers
        if identifier[0] == DOMAIN
    )

    higoal_device = None
    for dev in manager.device_map.values():
        if hasattr(dev, "id") and dev.id == higoal_device_id:
            higoal_device = dev
            break

    if higoal_device is None:
        return {"error": "device not found in manager", "device_id": higoal_device_id}

    return _device_as_dict(hass, higoal_device)


def _device_as_dict(hass: HomeAssistant, device) -> dict[str, Any]:
    """Represent a HIGOAL device as a diagnostics dictionary."""
    status_bytes = list(device._status) if device._status else None

    data: dict[str, Any] = async_redact_data(
        {
            "id": device.id,
            "type": device.type,
            "name": device.name,
            "model": device.model_name,
            "version": device.version,
            "home_id": device.home_id,
            "room_id": device.room_id,
            "mac": device.mac,
            "ssid": device.ssid,
        },
        REDACT_DEVICE,
    )

    data["status_raw"] = status_bytes

    data["entities"] = []
    for entity in device.entities:
        response_bytes = list(entity.response) if entity.response else None
        entity_data = {
            "id": entity.id,
            "name": entity.name,
            "type": entity.type,
            "is_online": entity.is_online(),
            "is_turned_on": entity.is_turned_on(),
            "percentage": entity.percentage(),
            "response_raw": response_bytes,
        }
        related = entity.get_related_entity()
        if related is not None:
            entity_data["related_entity_id"] = related.id
        data["entities"].append(entity_data)

    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    hass_device = device_registry.async_get_device(identifiers={(DOMAIN, device.id)})
    if hass_device:
        ha_entities = er.async_entries_for_device(
            entity_registry, device_id=hass_device.id, include_disabled_entities=True
        )
        data["home_assistant"] = {
            "name": hass_device.name,
            "name_by_user": hass_device.name_by_user,
            "disabled": hass_device.disabled,
            "disabled_by": hass_device.disabled_by,
            "entities": [],
        }
        for entity_entry in ha_entities:
            state = hass.states.get(entity_entry.entity_id)
            state_dict = dict(state.as_dict()) if state else None
            if state_dict:
                state_dict.pop("context", None)
            data["home_assistant"]["entities"].append(
                {
                    "entity_id": entity_entry.entity_id,
                    "disabled": entity_entry.disabled,
                    "disabled_by": entity_entry.disabled_by,
                    "entity_category": entity_entry.entity_category,
                    "device_class": entity_entry.device_class,
                    "original_device_class": entity_entry.original_device_class,
                    "state": state_dict,
                }
            )

    return data
