# modules/incidents.py - VERSIÓN COMPLETA CORREGIDA
"""
Módulo de incidencias DGT.
"""
import logging
from datetime import timedelta
from typing import Dict, List, Any
from collections import defaultdict
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util
from geopy.distance import geodesic

from .base import DGTModule
from ..api.incidents_client import DGTClient
from ..const import (
    CONF_RADIUS_KM,
    CONF_UPDATE_INTERVAL,
    CONF_MAX_AGE_DAYS,
    CONF_USE_CUSTOM_LOCATION,
    CONF_CUSTOM_LATITUDE,
    CONF_CUSTOM_LONGITUDE,
    DEFAULT_RADIUS_KM,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_MAX_AGE_DAYS,
)

_LOGGER = logging.getLogger(__name__)


class DGTIncidentsModule(DGTModule):
    """Módulo para incidencias DGT."""

    def __init__(self, hass: HomeAssistant, config: Dict[str, Any]):
        super().__init__(hass, config)
        self.name = "incidents"
        self.client = None

        if not hasattr(self, "user_lat") or self.user_lat is None:
            self._extract_coordinates_from_config(config)

        # CONFIGURACIÓN ESPECÍFICA DE INCIDENTS
        self.radius_km = config.get(CONF_RADIUS_KM, DEFAULT_RADIUS_KM)
        self.max_age_days = config.get(CONF_MAX_AGE_DAYS, DEFAULT_MAX_AGE_DAYS)
        self.update_interval = config.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

    def _extract_coordinates_from_config(self, config: Dict[str, Any]):
        """Extraer coordenadas directamente de config."""
        # 1. Coords personalizadas
        if config.get(CONF_USE_CUSTOM_LOCATION, False):
            self.user_lat = config.get(CONF_CUSTOM_LATITUDE)
            self.user_lon = config.get(CONF_CUSTOM_LONGITUDE)
        else:
            # 2. Coords de geopy
            self.user_lat = config.get(CONF_CUSTOM_LATITUDE) or config.get("latitude")
            self.user_lon = config.get(CONF_CUSTOM_LONGITUDE) or config.get("longitude")

        # 3. Fallback a HA config
        if self.user_lat is None or self.user_lon is None:
            self.user_lat = self.hass.config.latitude
            self.user_lon = self.hass.config.longitude

        if not hasattr(self, "use_custom_location"):
            self.use_custom_location = config.get(CONF_USE_CUSTOM_LOCATION, False)

    async def async_setup(self) -> bool:
        """Configurar módulo."""
        try:
            from homeassistant.helpers.aiohttp_client import async_get_clientsession

            session = async_get_clientsession(self.hass)
            self.client = DGTClient(session)

            update_interval = timedelta(minutes=self.update_interval)

            self.coordinator = DataUpdateCoordinator(
                self.hass,
                _LOGGER,
                name=f"dgt_incidents",
                update_method=self._async_update_data,
                update_interval=update_interval,
            )

            await self.coordinator.async_config_entry_first_refresh()

            self.enabled = True
            _LOGGER.info("Módulo de incidencias DGT configurado")
            return True

        except Exception as err:
            _LOGGER.error("Error configurando módulo incidencias: %s", err)
            return False

    async def _async_update_data(self) -> Dict[str, Any]:
        """Actualizar datos."""
        try:
            all_incidents = await self.client.get_incidents(self.max_age_days)
            nearby_incidents = []
            incidents_by_type = defaultdict(list)
            incidents_by_severity = defaultdict(list)

            for incident in all_incidents:
                distance = self._calculate_distance(incident)
                incident["distance_km"] = distance

                if distance <= self.radius_km:
                    nearby_incidents.append(incident)
                    inc_type = incident.get("type", "other")
                    incidents_by_type[inc_type].append(incident)
                    severity = incident.get("severity", "unknown")
                    incidents_by_severity[severity].append(incident)

            nearby_incidents.sort(key=lambda x: x.get("distance_km", 999))

            stats = self._prepare_statistics(
                all_incidents,
                nearby_incidents,
                dict(incidents_by_type),
                dict(incidents_by_severity),
            )

            _LOGGER.info(
                "DGT actualizado: %s total, %s cercanos (radio: %skm)",
                len(all_incidents),
                len(nearby_incidents),
                self.radius_km,
            )

            return {
                "all_incidents": all_incidents,
                "nearby_incidents": nearby_incidents,
                "incidents_by_type": dict(incidents_by_type),
                "incidents_by_severity": dict(incidents_by_severity),
                "statistics": stats,
                "last_update": dt_util.utcnow().isoformat(),
                "user_location": {
                    "latitude": self.user_lat,
                    "longitude": self.user_lon,
                    "radius_km": self.radius_km,
                },
            }

        except Exception as err:
            _LOGGER.error("Error actualizando datos DGT: %s", err)
            raise

    def _calculate_distance(self, incident: Dict) -> float:
        """Calcular distancia desde usuario a incidente en km."""
        try:
            inc_lat = incident.get("latitude")
            inc_lon = incident.get("longitude")

            if not inc_lat or not inc_lon:
                return 999.0

            user_coords = (self.user_lat, self.user_lon)
            inc_coords = (float(inc_lat), float(inc_lon))

            return geodesic(user_coords, inc_coords).kilometers
        except Exception:
            return 999.0

    def _prepare_statistics(
        self, all_incidents, nearby_incidents, incidents_by_type, incidents_by_severity
    ) -> Dict[str, Any]:
        """Preparar estadísticas."""
        stats = {
            "total": len(all_incidents),
            "nearby": len(nearby_incidents),
            "by_type": {},
            "by_severity": {},
            "closest": None,
            "most_severe": None,
        }

        for inc_type, incidents in incidents_by_type.items():
            stats["by_type"][inc_type] = len(incidents)

        for severity, incidents in incidents_by_severity.items():
            stats["by_severity"][severity] = len(incidents)

        if nearby_incidents:
            closest = min(nearby_incidents, key=lambda x: x.get("distance_km", 999))
            stats["closest"] = {
                "description": closest.get("description", ""),
                "distance_km": closest.get("distance_km", 0),
                "type": closest.get("type", ""),
                "severity": closest.get("severity", ""),
            }

        severity_order = {"highest": 4, "high": 3, "medium": 2, "low": 1, "unknown": 0}
        if nearby_incidents:
            most_severe = max(
                nearby_incidents,
                key=lambda x: severity_order.get(x.get("severity", "unknown"), 0),
            )
            stats["most_severe"] = {
                "description": most_severe.get("description", ""),
                "severity": most_severe.get("severity", ""),
                "type": most_severe.get("type", ""),
            }

        return stats

    @property
    def data(self) -> Dict[str, Any]:
        """Acceso a datos del coordinador."""
        return (
            self.coordinator.data if self.coordinator and self.coordinator.data else {}
        )

    @property
    def nearby_incidents(self) -> List[Dict]:
        """Incidentes cercanos."""
        return self.data.get("nearby_incidents", [])

    @property
    def incidents_by_type(self) -> Dict[str, List]:
        """Incidentes agrupados por tipo."""
        return self.data.get("incidents_by_type", {})

    @property
    def incidents_by_severity(self) -> Dict[str, List]:
        """Incidentes agrupados por severidad."""
        return self.data.get("incidents_by_severity", {})

    def async_add_listener(self, callback):
        """Exponer método del coordinador para los sensores."""
        if self.coordinator:
            return self.coordinator.async_add_listener(callback)
        return lambda: None

    def get_entities(self) -> List[Any]:
        """Obtener entidades."""
        return []
