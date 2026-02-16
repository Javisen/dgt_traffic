# modules/base.py
"""Base module for DGT Traffic."""

import logging
from typing import Dict, Any

from homeassistant.core import HomeAssistant

from ..const import (
    CONF_LOCATION_MODE,
    CONF_PERSON_ENTITY,
    CONF_CUSTOM_LATITUDE,
    CONF_CUSTOM_LONGITUDE,
    LOCATION_MODE_HA,
    LOCATION_MODE_CUSTOM,
    LOCATION_MODE_PERSON,
)

_LOGGER = logging.getLogger(__name__)


class DGTModule:
    """Base class for DGT modules."""

    def __init__(self, hass: HomeAssistant, config: Dict[str, Any]):
        """Initialize base module."""
        self.hass = hass
        self.config = config
        self.coordinator = None
        self.enabled = False
        self.user_lat = None
        self.user_lon = None
        self._location_mode = config.get(CONF_LOCATION_MODE, LOCATION_MODE_HA)

        # Las coordenadas se inicializarán en el módulo hijo
        # para poder tener listeners de persona

    def _update_coordinates_from_config(self):
        """Actualizar coordenadas según el modo configurado."""
        mode = self.config.get(CONF_LOCATION_MODE, LOCATION_MODE_HA)

        if mode == LOCATION_MODE_PERSON:
            person = self.config.get(CONF_PERSON_ENTITY)
            if person:
                state = self.hass.states.get(person)
                if state and state.attributes.get("latitude"):
                    self.user_lat = state.attributes["latitude"]
                    self.user_lon = state.attributes["longitude"]
                else:
                    self.user_lat = None
                    self.user_lon = None
            else:
                self.user_lat = None
                self.user_lon = None

        elif mode == LOCATION_MODE_CUSTOM:
            self.user_lat = self.config.get(CONF_CUSTOM_LATITUDE)
            self.user_lon = self.config.get(CONF_CUSTOM_LONGITUDE)

        else:  # LOCATION_MODE_HA
            self.user_lat = self.hass.config.latitude
            self.user_lon = self.hass.config.longitude

        self._validate_coordinates()

    def _validate_coordinates(self):
        """Validar coordenadas."""
        try:
            if self.user_lat is not None and self.user_lon is not None:
                float(self.user_lat)
                float(self.user_lon)
            else:
                self.user_lat = self.hass.config.latitude
                self.user_lon = self.hass.config.longitude
        except (ValueError, TypeError):
            self.user_lat = self.hass.config.latitude
            self.user_lon = self.hass.config.longitude

        if self.user_lat is None or self.user_lon is None:
            self.user_lat = 40.4168
            self.user_lon = -3.7038
            _LOGGER.warning("Usando coordenadas por defecto (Madrid)")

    async def async_setup(self) -> bool:
        """Setup module."""
        return True

    async def async_unload(self) -> None:
        """Unload module."""
        pass

    def async_add_listener(self, callback):
        """Add listener for updates."""
        if self.coordinator:
            return self.coordinator.async_add_listener(callback)
        return lambda: None

    @property
    def data(self) -> Dict[str, Any]:
        """Acceso a datos del coordinador."""
        return (
            self.coordinator.data if self.coordinator and self.coordinator.data else {}
        )

    @property
    def has_valid_location(self) -> bool:
        """Verificar si tenemos coordenadas válidas."""
        return (
            self.user_lat is not None
            and self.user_lon is not None
            and isinstance(self.user_lat, (int, float))
            and isinstance(self.user_lon, (int, float))
            and -90 <= self.user_lat <= 90
            and -180 <= self.user_lon <= 180
        )
