"""Binary sensor platform coordinator for DGT Traffic."""

import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up binary sensor platform - No binary sensors needed."""
    _LOGGER.info("Binary sensors de DGT Traffic no son necesarios")
    _LOGGER.info("Toda la información está disponible en los sensores normales")
    return True
