from homeassistant.components.cover import CoverEntity, CoverDeviceClass

from .higoal_client import Entity
from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
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


class HigoalCover(CoverEntity):
    """Representation of a smart blind."""

    def __init__(self, open_button: Entity, close_button: Entity):
        self._open_button = open_button
        self._close_button = close_button
        self._attr_unique_id = f"higoal:{open_button.device.id}:{open_button.id}"
        self._attr_name = open_button.name or 'Higoal Cover'

    @property
    def device_class(self):
        return CoverDeviceClass.BLIND

    def set_cover_position(self):
        value = int(self._open_button.percentage() * 100)
        self._attr_current_cover_position = 100 - value

    async def async_open_cover(self, **kwargs):
        self._open_button.turn_on()
        self.async_write_ha_state()

    async def async_close_cover(self, **kwargs):
        self._close_button.turn_on()
        self.async_write_ha_state()

    async def async_stop_cover(self, **kwargs):
        if self.is_closing:
            self._close_button.turn_off()
        elif self.is_opening:
            self._open_button.turn_off()
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
