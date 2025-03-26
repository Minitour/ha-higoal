"""Switch platform for higoal."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription

from .entity import HigoalEntity
from .higoal_client import Entity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import DataUpdateCoordinator
    from .data import HigoalConfigEntry

ENTITY_DESCRIPTIONS = (
    SwitchEntityDescription(
        key="higoal",
        name="Integration Switch",
        icon="mdi:format-quote-close",
    ),
)


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
            switches.append(
                HigoalSwitch(
                    button,
                    entry.runtime_data.coordinator,
                    SwitchEntityDescription(
                        key=f"higoal:{button.device.id}:{button.id}",
                        name=button.name or 'Unnamed Switch',
                        icon="mdi:format-quote-close",
                    )
                )
            )

    async_add_entities(switches, True)


class HigoalSwitch(HigoalEntity, SwitchEntity):
    """higoal switch class."""

    def __init__(
            self,
            entity: Entity,
            coordinator: DataUpdateCoordinator,
            entity_description: SwitchEntityDescription,
    ) -> None:
        """Initialize the switch class."""
        super().__init__(entity, coordinator)
        self.entity_description = entity_description

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self._entity.is_turned_on()

    async def async_turn_on(self, **_: Any) -> None:
        """Turn on the switch."""
        self._entity.turn_on()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **_: Any) -> None:
        """Turn off the switch."""
        self._entity.turn_off()
        await self.coordinator.async_request_refresh()
