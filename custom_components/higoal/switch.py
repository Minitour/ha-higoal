"""Switch platform for higoal."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .client import device
from .const import HIGOAL_DISCOVERY_NEW
from .data import HigoalConfigEntry
from .entity import BaseHigoalEntity


async def async_setup_entry(
        hass: HomeAssistant,
        entry: HigoalConfigEntry,
        async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    hass_data = entry.runtime_data

    @callback
    def async_discover_device(device_ids: list[str]) -> None:
        """Discover and add a discovered sensor."""
        entities: list[HigoalSwitch] = []
        for device_id in device_ids:
            higoal_device = hass_data.manager.device_map[device_id]
            for entity in higoal_device.entities:
                if entity.type != device.TYPE_SWITCH:
                    continue
                entities.append(entity)

        async_add_entities(entities)

    async_discover_device([*hass_data.manager.device_map])

    entry.async_on_unload(
        async_dispatcher_connect(hass, HIGOAL_DISCOVERY_NEW, async_discover_device)
    )


class HigoalSwitch(BaseHigoalEntity, SwitchEntity):
    """higoal switch class."""

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self.entity.is_turned_on()

    def turn_on(self, **kwargs: Any) -> None:
        self.entity.turn_on()

    def turn_off(self, **kwargs: Any) -> None:
        self.entity.turn_off()
