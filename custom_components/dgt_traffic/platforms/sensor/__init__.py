"""Sensor platform coordinator for DGT Traffic."""

import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up all sensor modules."""
    from custom_components.dgt_traffic import const

    _LOGGER.info("Configurando plataforma sensor (estructura modular)")

    config = {**config_entry.data}
    if config_entry.options:
        config.update(config_entry.options)

    all_entities = []

    if config.get(const.CONF_ENABLE_INCIDENTS, True):
        try:
            from .incidents import async_setup_entry as incidents_setup

            entities = await incidents_setup(hass, config_entry, async_add_entities)
            if entities:
                all_entities.extend(entities)
            _LOGGER.debug("Sensores de incidencias cargados")
        except Exception as err:
            _LOGGER.error("Error cargando sensores de incidencias: %s", err)

    if config.get(const.CONF_ENABLE_CHARGING, False):
        try:
            from .charging import async_setup_entry as charging_setup

            entities = await charging_setup(hass, config_entry, async_add_entities)
            if entities:
                all_entities.extend(entities)
            _LOGGER.debug("Sensores de electrolineras cargados")
        except Exception as err:
            _LOGGER.error("Error cargando sensores de electrolineras: %s", err)

    if all_entities:
        async_add_entities(all_entities, update_before_add=False)

    _LOGGER.info("Plataforma sensor configurada: %d entidades", len(all_entities))
    return True
