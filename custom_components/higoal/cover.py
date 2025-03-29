from __future__ import annotations

from homeassistant.components.cover import CoverEntity, CoverDeviceClass
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .higoal_client import Entity


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback):
    """Set up the cover platform."""
    devices = entry.runtime_data.coordinator.devices
    covers = []
    for device in devices:
        for button in device.buttons:
            if button.type != 3:
                continue
            if button.name == '':
                continue

            open_blind = button
            close_blind = button.get_related_entity()

            covers.append(HigoalCover(entry.runtime_data.coordinator, open_blind, close_blind))

    async_add_entities(covers, True)


class HigoalCover(CoordinatorEntity, CoverEntity):
    """Representation of a smart blind."""

    def __init__(self, coordinator, open_button: Entity, close_button: Entity):
        super().__init__(coordinator)
        self._open_button = open_button
        self._close_button = close_button
        self._attr_unique_id = f"higoal:{open_button.device.id}:{open_button.id}"
        self._attr_name = open_button.name or 'Higoal Cover'
        self._is_closed = False
        self._cover_position = 0
        self._is_closing = False
        self._is_opening = False
        self._is_available = True

    @property
    def device_class(self):
        return CoverDeviceClass.SHUTTER

    @property
    def current_cover_position(self):
        """Return the position of the cover (0 = closed, 100 = open)."""
        return self._cover_position

    @property
    def is_closed(self) -> bool | None:
        return self._is_closed

    @property
    def is_closing(self) -> bool | None:
        return self._is_closing

    @property
    def is_opening(self) -> bool | None:
        return self._is_opening

    @property
    def is_available(self) -> bool:
        return self._is_available

    async def async_open_cover(self, **kwargs):
        await self._open_button.turn_on()
        self._is_opening = True
        self.async_write_ha_state()

    async def async_close_cover(self, **kwargs):
        await self._close_button.turn_on()
        self._is_closing = True
        self.async_write_ha_state()

    async def async_stop_cover(self, **kwargs):
        percentage = None
        if self._is_closing:
            await self._close_button.turn_off()
            percentage = await self._close_button.percentage(use_cache=False)
        elif self._is_opening:
            await self._open_button.turn_off()
            percentage = await self._open_button.percentage(use_cache=False)

        if percentage is not None:
            self._cover_position = self._calculate_position(percentage)
            self._is_closed = self._cover_position == 0
            self._is_closing = False
            self._is_opening = False

        self.async_write_ha_state()

    @staticmethod
    def _calculate_position(percentage: float | None) -> int | None:
        if percentage is None:
            return None
        return 100 - int(percentage * 100)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        open_data = self.coordinator.data.get(f'higoal:{self._open_button.device.id}:{self._open_button.id}')
        close_data = self.coordinator.data.get(f'higoal:{self._close_button.device.id}:{self._close_button.id}')

        self._open_button = open_data['entity']
        self._close_button = close_data['entity']
        self._cover_position = self._calculate_position(open_data['state']['percentage'])
        self._is_closed = self._cover_position == 0
        self._is_opening = open_data['state']['is_turned_on']
        self._is_closing = close_data['state']['is_turned_on']
        self._available = open_data['state']['is_online']
        self.async_write_ha_state()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._open_button.device.id)},
            "name": self._open_button.device.name,
            "manufacturer": "HIGOAL",
            "model": self._open_button.device.model_name,
            "sw_version": self._open_button.device.version,
        }
