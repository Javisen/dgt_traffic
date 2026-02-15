"""Sensor platform redirection for DGT Traffic modular structure."""

import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Redirect to modular sensor platform."""
    from .platforms.sensor import async_setup_entry as modular_setup

    _LOGGER.debug("Redirigiendo sensor platform a estructura modular")
    return await modular_setup(hass, config_entry, async_add_entities)
