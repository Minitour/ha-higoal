from __future__ import annotations

from datetime import timedelta
from xml.etree.ElementPath import prepare_parent

from homeassistant.components.cover import CoverEntity, CoverDeviceClass
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.event import async_track_time_interval

from .higoal_client import Entity
from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback):
    """Set up the cover platform."""
    devices = await entry.runtime_data.higoal_client.get_devices()
    covers = []
    for device in devices:
        for button in device.buttons:
            if button.type != 3:
                continue
            if button.name == '':
                continue

            open_blind = button
            close_blind = button.get_related_entity()

            covers.append(HigoalCover(open_blind, close_blind))

    async_add_entities(covers, True)
    for cover in covers:
        async_track_time_interval(hass, cover.refresh, timedelta(seconds=30))


class HigoalCover(CoverEntity):
    """Representation of a smart blind."""

    def __init__(self, open_button: Entity, close_button: Entity):
        self._open_button = open_button
        self._close_button = close_button
        self._attr_unique_id = f"higoal:{open_button.device.id}:{open_button.id}"
        self._attr_name = open_button.name or 'Higoal Cover'
        self._is_closed = False
        self._cover_position = 0
        self._is_closing = False
        self._is_opening = False

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

    async def async_open_cover(self, **kwargs):
        await self._open_button.turn_on()
        self._is_opening = True
        self.schedule_update_ha_state()

    async def async_close_cover(self, **kwargs):
        await self._close_button.turn_on()
        self._is_closing= True
        self.schedule_update_ha_state()

    async def async_stop_cover(self, **kwargs):
        if self.is_closing:
            await self._close_button.turn_off()
        elif self.is_opening:
            await self._open_button.turn_off()
        self.schedule_update_ha_state()

    async def refresh(self, *args, **kwargs):
        value = int(await self._open_button.percentage(use_cache=False) * 100)
        self._cover_position = 100 - value
        self._is_closed = self._cover_position == 0
        self._close_button.response = self._open_button.response

        # the following statements use the cached response
        self._is_opening = await self._open_button.is_turned_on()
        self._is_closing = await self._close_button.is_turned_on()
        self.schedule_update_ha_state()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._open_button.device.id)},
            "name": self._open_button.device.name,
            "manufacturer": "HIGOAL",
            "model": self._open_button.device.model_name,
            "sw_version": self._open_button.device.version,
        }
