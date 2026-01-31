"""The DGT Traffic integration."""

import logging
from datetime import timedelta

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

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
    PLATFORMS,
)
from .coordinator import DGTCoordinator
from .api.dgt_client import DGTClient

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
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
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up DGT Traffic from a config entry."""
    _LOGGER.info("Setting up DGT Traffic integration")

    # Añadir coordenadas de HA a la configuración
    config_data = dict(entry.data)
    config_data["latitude"] = hass.config.latitude
    config_data["longitude"] = hass.config.longitude

    # Create session and client
    session = async_get_clientsession(hass)
    client = DGTClient(session)

    # Create coordinator with enhanced config
    coordinator = DGTCoordinator(hass, client, config_data)

    # Store coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Load platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Start initial refresh
    await coordinator.async_config_entry_first_refresh()

    # Setup update listener
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    _LOGGER.info("DGT Traffic integration setup complete")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading DGT Traffic integration")

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)
