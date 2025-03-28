"""
Custom integration to integrate higoal with Home Assistant.

For more details about this integration, please refer to
https://github.com/ludeeus/integration_blueprint
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.loader import async_get_loaded_integration

from .const import DOMAIN, LOGGER
from .coordinator import Coordinator
from .data import IntegrationData
from .higoal_client import HigoalApiClient

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import HigoalConfigEntry

PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.COVER
]


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(
        hass: HomeAssistant,
        entry: HigoalConfigEntry,
) -> bool:
    """Set up this integration using UI."""
    api = HigoalApiClient(
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        session=async_get_clientsession(hass),
    )
    await api.connect()

    data_coordinator = Coordinator(hass, entry, api)
    await data_coordinator.async_config_entry_first_refresh()

    entry.runtime_data = IntegrationData(
        higoal_client=api,
        coordinator=data_coordinator,
        integration=async_get_loaded_integration(hass, entry.domain)
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(
        hass: HomeAssistant,
        entry: HigoalConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
        hass: HomeAssistant,
        entry: HigoalConfigEntry,
) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
