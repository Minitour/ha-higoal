"""Adds config flow for Blueprint."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import selector
from slugify import slugify

from .client.api import Api
from .const import DOMAIN, logger


class FlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Blueprint."""

    VERSION = 1

    async def async_step_user(
            self,
            user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            try:
                self._test_credentials(
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                )
            except Exception as e:
                logger.warning(e)
                _errors["base"] = "auth"
            else:
                await self.async_set_unique_id(
                    unique_id=slugify(user_input[CONF_USERNAME])
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME,
                        default=(user_input or {}).get(CONF_USERNAME, vol.UNDEFINED),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT,
                        ),
                    ),
                    vol.Required(CONF_PASSWORD): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD,
                        ),
                    )
                },
            ),
            errors=_errors,
        )

    def _test_credentials(self, username: str, password: str) -> None:
        """Validate credentials."""
        api = Api(username=username, password=password)
        api.sign_in()
