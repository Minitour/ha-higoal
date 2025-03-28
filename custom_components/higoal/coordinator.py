from datetime import timedelta

import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import LOGGER as _LOGGER


class Coordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    def __init__(
            self,
            hass: HomeAssistant,
            config_entry: ConfigEntry,
            api: 'HigoalApiClient',
            update_interval: timedelta = timedelta(minutes=1)
    ):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="Higoal Data Coordinator",
            config_entry=config_entry,
            update_interval=update_interval,
            always_update=True
        )
        self.api = api
        self.devices = []

    async def _async_setup(self):
        """Set up the coordinator

        This is the place to set up your coordinator,
        or to load data, that only needs to be loaded once.

        This method will be called automatically during
        coordinator.async_config_entry_first_refresh.
        """
        pass

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        data = dict()
        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with async_timeout.timeout(10):
                devices = await self.api.get_devices()
                self.devices = devices
                for device in devices:
                    for button in device.buttons:
                        data[f'higoal:{button.device.id}:{button.id}']['entity'] = button
                        data[f'higoal:{button.device.id}:{button.id}']['state'] = {
                            'is_turned_on': await button.is_turned_on(),
                            'is_online': await button.is_online(),
                            'percentage': await button.percentage()
                        }
            return data
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")
