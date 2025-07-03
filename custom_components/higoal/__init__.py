"""
Custom integration to integrate higoal with Home Assistant.

For more details about this integration, please refer to
https://github.com/ludeeus/integration_blueprint
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import dispatcher_send

from .client.device import Entity, Device
from .client.manager import Manager, EntityListener
from .const import DOMAIN, logger, HIGOAL_HA_SIGNAL_UPDATE_ENTITY, HIGOAL_DISCOVERY_NEW
from .data import IntegrationData

from homeassistant.core import HomeAssistant, callback

from .data import HigoalConfigEntry

PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.LIGHT, Platform.COVER]


class HomeAssistantEntityListener(EntityListener):

    def __init__(self, hass: HomeAssistant):
        self.hass = hass

    def on_entity_changed(self, entity: Entity):
        dispatcher_send(
            self.hass,
            f"{HIGOAL_HA_SIGNAL_UPDATE_ENTITY}_{entity.device.id}_{entity.id}",
            [],
        )

    def on_device_added(self, device: Device):
        self.hass.add_job(self.async_remove_device, device.id)

        dispatcher_send(self.hass, HIGOAL_DISCOVERY_NEW, [device.identifier])

    def on_device_removed(self, device: Device) -> None:
        """Add device removed listener."""
        self.hass.add_job(self.async_remove_device, device.id)

    @callback
    def async_remove_device(self, device_id: str) -> None:
        """Remove device from Home Assistant."""
        device_registry = dr.async_get(self.hass)
        device_entry = device_registry.async_get_device(
            identifiers={(DOMAIN, device_id)}
        )
        if device_entry is not None:
            device_registry.async_remove_device(device_entry.id)


async def async_setup_entry(hass: HomeAssistant, entry: HigoalConfigEntry) -> bool:
    """Async setup hass config entry."""

    device_listener = HomeAssistantEntityListener(hass)
    manager = Manager(
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        entity_listener=device_listener
    )

    # Get all devices
    await hass.async_add_executor_job(manager.get_devices)

    # Connection is successful, store the manager & listener
    entry.runtime_data = IntegrationData(manager=manager, listener=device_listener)

    device_registry = dr.async_get(hass)
    for device in manager.device_map.values():
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, device.id)},
            manufacturer="HIGOAL",
            name=device.name,
            model=device.model_name,
            sw_version=device.version
        )

    # Notify platforms of setup
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # start background listener
    await hass.async_add_executor_job(manager.refresh)
    return True


async def async_unload_entry(
        hass: HomeAssistant,
        entry: HigoalConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        runtime_data = entry.runtime_data
        if runtime_data.manager.mq is not None:
            runtime_data.manager.mq.stop()
    return unload_ok


async def async_reload_entry(
        hass: HomeAssistant,
        entry: HigoalConfigEntry,
) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
