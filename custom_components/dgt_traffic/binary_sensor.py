"""Binary sensor platform redirection for DGT Traffic."""

import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up binary sensor platform - No binary sensors implemented."""
    _LOGGER.debug("Binary sensors no implementados (uso sensores normales)")
    return True
