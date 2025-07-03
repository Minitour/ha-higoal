from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity as HomeAssistantEntity
from .const import DOMAIN, HIGOAL_HA_SIGNAL_UPDATE_ENTITY
from .client.device import Entity


class BaseHigoalEntity(HomeAssistantEntity):

    def __init__(self, entity: Entity):
        self.entity = entity
        self._attr_unique_id = f"higoal:{entity.device.id}:{entity.id}"
        self._attr_name = entity.name or "Higoal Entity"

    @property
    def available(self):
        return self.entity.is_online()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.entity.device.id)},
            "name": self.entity.device.name,
            "manufacturer": "HIGOAL",
            "model": self.entity.device.model_name,
            "sw_version": self.entity.device.version,
        }

    async def async_added_to_hass(self) -> None:
        """Call when entity is added to hass."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{HIGOAL_HA_SIGNAL_UPDATE_ENTITY}_{self.entity.device.id}_{self.entity.id}",
                self._handle_state_update,
            )
        )

    async def _handle_state_update(
            self, updated_status_properties: list[str] | None
    ) -> None:
        self.async_write_ha_state()
