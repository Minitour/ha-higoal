"""Light platform for higoal."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import LightEntity, ATTR_BRIGHTNESS, ColorMode
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
        entities: list[HigoalLight] = []
        for device_id in device_ids:
            higoal_device = hass_data.manager.device_map[device_id]
            for entity in higoal_device.entities:
                if entity.type != device.TYPE_DIMMER:
                    continue
                entities.append(entity)

        async_add_entities(entities)

    async_discover_device([*hass_data.manager.device_map])

    entry.async_on_unload(
        async_dispatcher_connect(hass, HIGOAL_DISCOVERY_NEW, async_discover_device)
    )


class HigoalLight(BaseHigoalEntity, LightEntity):
    """Higoal light with dimmer support."""

    @property
    def is_on(self) -> bool:
        """Return true if the light is on."""
        return self.entity.is_turned_on()

    @property
    def brightness(self) -> int | None:
        """Return the current brightness (0..255)."""
        return int(self.entity.percentage() * 255)

    @property
    def supported_color_modes(self) -> set[str]:
        return {ColorMode.BRIGHTNESS}

    @property
    def color_mode(self) -> str:
        return ColorMode.BRIGHTNESS

    def turn_on(self, **kwargs: Any) -> None:
        if ATTR_BRIGHTNESS in kwargs:
            value = kwargs[ATTR_BRIGHTNESS]
            self.entity.set_percentage(int(value / 255))
        else:
            self.entity.turn_on()

    def turn_off(self, **kwargs: Any) -> None:
        self.entity.turn_off()
