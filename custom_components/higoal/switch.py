"""Switch platform for higoal."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity

from .const import DOMAIN
from .data import HigoalConfigEntry
from .higoal_client import Entity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
        hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
        entry: HigoalConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    devices = await entry.runtime_data.higoal_client.get_devices()
    switches = []

    for device in devices:
        for button in device.buttons:
            if button.type != 1:
                continue

            switches.append(HigoalSwitch(button))

    async_add_entities(switches, True)


class HigoalSwitch(SwitchEntity):
    """higoal switch class."""

    def __init__(
            self,
            entity: Entity
    ) -> None:
        """Initialize the switch class."""
        self._entity = entity
        self._attr_unique_id = f"higoal:{entity.device.id}:{entity.id}"
        self._attr_name = entity.name or 'Higoal Switch'

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self._entity.is_turned_on()

    async def async_turn_on(self, **_: Any) -> None:
        """Turn on the switch."""
        self._entity.turn_on()
        self.async_write_ha_state()

    async def async_turn_off(self, **_: Any) -> None:
        """Turn off the switch."""
        self._entity.turn_off()
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
