"""Light platform for higoal."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import LightEntity, ATTR_BRIGHTNESS, ColorMode
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .data import HigoalConfigEntry
from .higoal_client import Entity


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: HigoalConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the light platform."""
    devices = entry.runtime_data.coordinator.devices
    lights = []

    for device in devices:
        for button in device.buttons:
            if button.type != 2:
                continue

            lights.append(HigoalLight(entry.runtime_data.coordinator, button))

    async_add_entities(lights, True)


class HigoalLight(CoordinatorEntity, LightEntity):
    """Higoal light with dimmer support."""

    def __init__(self, coordinator, entity: Entity) -> None:
        super().__init__(coordinator)
        self._entity = entity
        self._attr_unique_id = f"higoal:{entity.device.id}:{entity.id}"
        self._attr_name = entity.name or "Higoal Light"
        self._is_on = False
        self._brightness = 255  # Full brightness by default
        self._available = True

    @property
    def is_on(self) -> bool:
        """Return true if the light is on."""
        return self._is_on

    @property
    def brightness(self) -> int | None:
        """Return the current brightness (0..255)."""
        return self._brightness

    @property
    def supported_color_modes(self) -> set[str]:
        return {ColorMode.BRIGHTNESS}

    @property
    def color_mode(self) -> str:
        return ColorMode.BRIGHTNESS

    @property
    def available(self):
        return self._available

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on with optional brightness."""
        if ATTR_BRIGHTNESS in kwargs:
            self._brightness = kwargs[ATTR_BRIGHTNESS]
            await self._entity.set_percentage(int(self._brightness / 255 * 100))
        else:
            await self._entity.turn_on()

        self._is_on = await self._entity.is_turned_on()
        self._brightness = int((await self._entity.percentage() / 100) * 255)
        self.async_write_ha_state()

    async def async_turn_off(self, **_: Any) -> None:
        """Turn the light off."""
        await self._entity.turn_off()
        self._is_on = await self._entity.is_turned_on()
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.coordinator.data.get(self._attr_unique_id)
        self._entity = data["entity"]
        self._is_on = data["state"]["is_turned_on"]
        self._brightness = int(data["state"].get("percentage", 100) / 100 * 255)
        self._available = data["state"]["is_online"]
        self.async_write_ha_state()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entity.device.id)},
            "name": self._entity.device.name,
            "manufacturer": "HIGOAL",
            "model": self._entity.device.model_name,
            "sw_version": self._entity.device.version,
        }
