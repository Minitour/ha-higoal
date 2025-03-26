"""BlueprintEntity class."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .higoal_client import Entity
from .const import ATTRIBUTION
from .coordinator import DataUpdateCoordinator


class HigoalEntity(CoordinatorEntity[DataUpdateCoordinator]):
    """BlueprintEntity class."""

    _attr_attribution = ATTRIBUTION

    def __init__(self, entity: Entity, coordinator: DataUpdateCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._entity = entity
        self._attr_unique_id = f"{entity.device.id}-{entity.id}"
        self._attr_device_info = DeviceInfo(
            identifiers={
                (
                    coordinator.config_entry.domain,
                    entity.device.id,
                ),
            },
        )
