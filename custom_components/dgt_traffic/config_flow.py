"""Config flow for DGT Traffic."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_RADIUS_KM,
    CONF_UPDATE_INTERVAL,
    CONF_MAX_AGE_DAYS,
    CONF_MUNICIPALITY,
    CONF_PROVINCE,
    DEFAULT_RADIUS_KM,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_MAX_AGE_DAYS,
)


class DGTConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for DGT Traffic."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:

            # Create unique ID from municipality or random
            if user_input.get(CONF_MUNICIPALITY):
                unique_id = (
                    f"dgt_{user_input[CONF_MUNICIPALITY].lower().replace(' ', '_')}"
                )
                if user_input.get(CONF_PROVINCE):
                    unique_id += (
                        f"_{user_input[CONF_PROVINCE].lower().replace(' ', '_')}"
                    )
            else:
                import time

                unique_id = f"dgt_{int(time.time())}"

            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            # Create title
            title = "DGT Tráfico"
            if user_input.get(CONF_MUNICIPALITY):
                title = f"DGT Tráfico - {user_input[CONF_MUNICIPALITY]}"
                if user_input.get(CONF_PROVINCE):
                    title += f" ({user_input[CONF_PROVINCE]})"

            return self.async_create_entry(title=title, data=user_input)

        data_schema = vol.Schema(
            {
                vol.Optional(CONF_MUNICIPALITY, default=""): str,
                vol.Optional(CONF_PROVINCE, default=""): str,
                vol.Optional(CONF_RADIUS_KM, default=DEFAULT_RADIUS_KM): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=500)
                ),
                vol.Optional(
                    CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=1440)),
                vol.Optional(CONF_MAX_AGE_DAYS, default=DEFAULT_MAX_AGE_DAYS): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=30)
                ),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return DGTOptionsFlow(config_entry)


class DGTOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for DGT Traffic."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_MUNICIPALITY,
                    default=self.config_entry.options.get(CONF_MUNICIPALITY, ""),
                ): str,
                vol.Optional(
                    CONF_PROVINCE,
                    default=self.config_entry.options.get(CONF_PROVINCE, ""),
                ): str,
                vol.Optional(
                    CONF_RADIUS_KM,
                    default=self.config_entry.options.get(
                        CONF_RADIUS_KM, DEFAULT_RADIUS_KM
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=500)),
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=1440)),
                vol.Optional(
                    CONF_MAX_AGE_DAYS,
                    default=self.config_entry.options.get(
                        CONF_MAX_AGE_DAYS, DEFAULT_MAX_AGE_DAYS
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)
