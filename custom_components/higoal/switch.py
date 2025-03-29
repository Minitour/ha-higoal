"""Switch platform for higoal."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, logger
from .data import HigoalConfigEntry
from .higoal_client import Entity


async def async_setup_entry(
        hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
        entry: HigoalConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    devices = entry.runtime_data.coordinator.devices
    switches = []

    for device in devices:
        for button in device.buttons:
            if button.type != 1:
                continue

            switches.append(HigoalSwitch(entry.runtime_data.coordinator, button))

    async_add_entities(switches, True)


class HigoalSwitch(CoordinatorEntity, SwitchEntity):
    """higoal switch class."""

    def __init__(
            self,
            coordinator,
            entity: Entity
    ) -> None:
        super().__init__(coordinator)
        """Initialize the switch class."""
        self._entity = entity
        self._attr_unique_id = f"higoal:{entity.device.id}:{entity.id}"
        self._attr_name = entity.name or 'Higoal Switch'
        self._state = False
        self._available = True

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self._state

    @property
    def available(self):
        """Return True if entity is available."""
        return self._available

    async def async_turn_on(self, **_: Any) -> None:
        """Turn on the switch."""
        await self._entity.turn_on()
        self._state = await self._entity.is_turned_on()
        self.async_write_ha_state()

    async def async_turn_off(self, **_: Any) -> None:
        """Turn off the switch."""
        await self._entity.turn_off()
        self._state = await self._entity.is_turned_on()
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.coordinator.data.get(self._attr_unique_id)
        logger.debug('[%s] Updated data: %s', self._attr_unique_id, data)
        self._entity = data['entity']
        self._state = data['state']['is_turned_on']
        self._available = data['state']['is_online']
        self.async_write_ha_state()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entity.device.id)},  # Same ID as the cover
            "name": self._entity.device.name,
            "manufacturer": "HIGOAL",
            "model": self._entity.device.model_name,
            "sw_version": self._entity.device.version,
        }
