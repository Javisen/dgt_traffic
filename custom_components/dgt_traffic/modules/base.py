# modules/base.py
"""Base module for DGT Traffic."""

import logging
from typing import Dict, Any

from homeassistant.core import HomeAssistant

from ..const import (
    CONF_USE_CUSTOM_LOCATION,
    CONF_CUSTOM_LATITUDE,
    CONF_CUSTOM_LONGITUDE,
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

        # === CALCULAR COORDENADAS DEL USUARIO  ===
        _LOGGER.debug("=== BASE MODULE: Calculando coordenadas ===")
        _LOGGER.debug("Config keys: %s", list(config.keys()))
        _LOGGER.debug(
            "CONF_USE_CUSTOM_LOCATION: %s", config.get(CONF_USE_CUSTOM_LOCATION, False)
        )
        _LOGGER.debug("CONF_CUSTOM_LATITUDE: %s", config.get(CONF_CUSTOM_LATITUDE))
        _LOGGER.debug("CONF_CUSTOM_LONGITUDE: %s", config.get(CONF_CUSTOM_LONGITUDE))
        _LOGGER.debug("HA config latitude: %s", hass.config.latitude)
        _LOGGER.debug("HA config longitude: %s", hass.config.longitude)

        # Determinar qué coordenadas usar
        use_custom = config.get(CONF_USE_CUSTOM_LOCATION, False)

        if use_custom:
            # Usar ubicación personalizada
            custom_lat = config.get(CONF_CUSTOM_LATITUDE)
            custom_lon = config.get(CONF_CUSTOM_LONGITUDE)

            if custom_lat is not None and custom_lon is not None:
                self.user_lat = float(custom_lat)
                self.user_lon = float(custom_lon)
                self.use_custom_location = True
                _LOGGER.info(
                    "📍 BASE: Usando ubicación PERSONALIZADA: %s, %s",
                    self.user_lat,
                    self.user_lon,
                )
            else:
                # Coordenadas personalizadas no configuradas
                self.user_lat = hass.config.latitude
                self.user_lon = hass.config.longitude
                self.use_custom_location = False
                _LOGGER.warning(
                    "⚠️ BASE: Configuración personalizada activada pero sin coordenadas. Usando HA: %s, %s",
                    self.user_lat,
                    self.user_lon,
                )
        else:
            # Usar ubicación de Home Assistant
            self.user_lat = hass.config.latitude
            self.user_lon = hass.config.longitude
            self.use_custom_location = False
            _LOGGER.info(
                "📍 BASE: Usando ubicación de HOME ASSISTANT: %s, %s",
                self.user_lat,
                self.user_lon,
            )

        # Validación final
        if self.user_lat is None or self.user_lon is None:
            _LOGGER.error(
                "❌ BASE: Coordenadas del usuario son None después del cálculo"
            )
            _LOGGER.error(
                "   HA location: %s, %s", hass.config.latitude, hass.config.longitude
            )
            _LOGGER.error("   Config: %s", config)

            # Fallback a coordenadas por defecto (España central)
            self.user_lat = 40.4168  # Madrid
            self.user_lon = -3.7038
            _LOGGER.warning(
                "⚠️ BASE: Usando coordenadas por defecto: %s, %s",
                self.user_lat,
                self.user_lon,
            )

        _LOGGER.info(
            "📍 BASE: Coordenadas finales: %s, %s", self.user_lat, self.user_lon
        )
        _LOGGER.info(
            "📍 BASE: Usando ubicación personalizada: %s", self.use_custom_location
        )

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

    # Propiedades comunes
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
