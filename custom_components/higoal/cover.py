from __future__ import annotations

from typing import Any

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .client import device
from .const import DOMAIN
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
        entities: list[HigoalCover] = []
        for device_id in device_ids:
            higoal_device = hass_data.manager.device_map[device_id]
            for entity in higoal_device.entities:
                if entity.type != device.TYPE_SHUTTER:
                    continue
                entities.append(entity)

        async_add_entities(entities)

    async_discover_device([*hass_data.manager.device_map])

    entry.async_on_unload(
        async_dispatcher_connect(hass, HIGOAL_DISCOVERY_NEW, async_discover_device)
    )


class HigoalCover(BaseHigoalEntity, CoverEntity):
    """Representation of a smart blind."""

    def __init__(self, open_button: device.Entity, close_button: device.Entity):
        super().__init__(open_button)
        self._open_button = open_button
        self._close_button = close_button
        self._is_closed = False
        self._cover_position = 0
        self._is_closing = False
        self._is_opening = False

    @property
    def supported_features(self) -> CoverEntityFeature:
        return (
                CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
        )

    @property
    def device_class(self):
        return CoverDeviceClass.SHUTTER

    @property
    def current_cover_position(self):
        """Return the position of the cover (0 = closed, 100 = open)."""
        current_percentage = self._open_button.percentage()
        return self._calculate_position(current_percentage)

    @property
    def is_closed(self) -> bool | None:
        current_percentage = self._open_button.percentage()
        return self._calculate_position(current_percentage) == 0

    @property
    def is_closing(self) -> bool | None:
        return self._close_button.is_turned_on()

    @property
    def is_opening(self) -> bool | None:
        return self._open_button.is_turned_on()

    def open_cover(self, **kwargs: Any) -> None:
        self._open_button.turn_on()
        self._is_opening = True

    def close_cover(self, **kwargs: Any) -> None:
        self._close_button.turn_on()
        self._is_closing = True

    def stop_cover(self, **kwargs: Any) -> None:
        if self.is_closing:
            self._close_button.turn_off()
        elif self.is_opening:
            self._open_button.turn_off()

    @staticmethod
    def _calculate_position(percentage: float | None) -> int | None:
        if percentage is None:
            return None
        return 100 - int(percentage * 100)
