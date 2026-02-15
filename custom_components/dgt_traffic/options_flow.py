"""Options flow modular para DGT Traffic."""

from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
import logging

from .const import (
    CONF_ENABLE_INCIDENTS,
    CONF_ENABLE_CHARGING,
    CONF_RADIUS_KM,
    CONF_UPDATE_INTERVAL,
    CONF_MAX_AGE_DAYS,
    CONF_CHARGING_RADIUS_KM,
    CONF_SHOW_ONLY_AVAILABLE,
    DEFAULT_RADIUS_KM,
    DEFAULT_CHARGING_RADIUS_KM,
    DEFAULT_UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class DGTOptionsFlow(config_entries.OptionsFlow):
    """Options flow modular para DGT Traffic."""

    def __init__(self, entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        self.entry = entry
        self.data = {**entry.data, **entry.options}

    async def async_step_init(self, user_input=None):
        """Detectar módulo y redirigir al menú correcto."""
        if self.data.get(CONF_ENABLE_INCIDENTS):
            return await self.async_step_incidents()

        if self.data.get(CONF_ENABLE_CHARGING):
            return await self.async_step_charging()

        return await self.async_step_incidents()

    # --------OPCIONES DEL MÓDULO DE INCIDENCIAS---------

    async def async_step_incidents(self, user_input=None):
        """Opciones del módulo de incidencias."""
        if user_input is not None:
            _LOGGER.debug("Actualizando opciones de Incidencias: %s", user_input)
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_RADIUS_KM,
                    default=self.data.get(CONF_RADIUS_KM, DEFAULT_RADIUS_KM),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=500)),
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=self.data.get(
                        CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=1440)),
                vol.Optional(
                    CONF_MAX_AGE_DAYS,
                    default=self.data.get(CONF_MAX_AGE_DAYS, 1),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
            }
        )

        return self.async_show_form(step_id="incidents", data_schema=schema)

    # ------OPCIONES DEL MÓDULO DE ELECTROLINERAS-------

    async def async_step_charging(self, user_input=None):
        """Opciones del módulo de electrolineras."""
        if user_input is not None:
            _LOGGER.debug("Actualizando opciones de Electrolineras: %s", user_input)
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_CHARGING_RADIUS_KM,
                    default=self.data.get(
                        CONF_CHARGING_RADIUS_KM, DEFAULT_CHARGING_RADIUS_KM
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=500)),
                vol.Optional(
                    CONF_SHOW_ONLY_AVAILABLE,
                    default=self.data.get(CONF_SHOW_ONLY_AVAILABLE, True),
                ): bool,
            }
        )

        return self.async_show_form(step_id="charging", data_schema=schema)
