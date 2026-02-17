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

from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.core import callback

from ..const import (
    CONF_RADIUS_KM,
    CONF_MAX_AGE_DAYS,
    CONF_UPDATE_INTERVAL,
    CONF_LOCATION_MODE,
    CONF_PERSON_ENTITY,
    CONF_CUSTOM_LATITUDE,
    CONF_CUSTOM_LONGITUDE,
    LOCATION_MODE_HA,
    LOCATION_MODE_CUSTOM,
    LOCATION_MODE_PERSON,
    DEFAULT_RADIUS_KM,
    DEFAULT_MAX_AGE_DAYS,
    DEFAULT_UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class DGTIncidentsModule(DGTModule):
    """Módulo para incidencias DGT."""

    def __init__(self, hass: HomeAssistant, config: Dict[str, Any]):
        """Initialize incidents module."""
        super().__init__(hass, config)
        self.name = "incidents"
        self.client = None
        self._location_listener = None

        # Inicializar coordenadas según modo
        self._update_coordinates_from_config()

        # CONFIGURACIÓN ESPECÍFICA DE INCIDENTS
        self.radius_km = config.get(CONF_RADIUS_KM, DEFAULT_RADIUS_KM)
        self.max_age_days = config.get(CONF_MAX_AGE_DAYS, DEFAULT_MAX_AGE_DAYS)
        self.update_interval = config.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

    def _update_coordinates_from_config(self):
        """Actualizar coordenadas según el modo configurado."""
        mode = self.config.get(CONF_LOCATION_MODE, LOCATION_MODE_HA)

        if mode == LOCATION_MODE_PERSON:
            # Para persona, obtenemos del estado actual
            person = self.config.get(CONF_PERSON_ENTITY)
            if person:
                state = self.hass.states.get(person)
                if state and state.attributes.get("latitude"):
                    self.user_lat = state.attributes["latitude"]
                    self.user_lon = state.attributes["longitude"]
                    _LOGGER.debug(
                        "Coordenadas desde persona %s: %s, %s",
                        person,
                        self.user_lat,
                        self.user_lon,
                    )
                else:
                    self.user_lat = None
                    self.user_lon = None
            else:
                self.user_lat = None
                self.user_lon = None

        elif mode == LOCATION_MODE_CUSTOM:
            # Coordenadas fijas del config
            self.user_lat = self.config.get(CONF_CUSTOM_LATITUDE)
            self.user_lon = self.config.get(CONF_CUSTOM_LONGITUDE)

        else:  # LOCATION_MODE_HA
            # Fallback a HA
            self.user_lat = self.hass.config.latitude
            self.user_lon = self.hass.config.longitude

        # Validar coordenadas
        self._validate_coordinates()

    def _validate_coordinates(self):
        """Validar que las coordenadas son números válidos."""
        try:
            if self.user_lat is not None and self.user_lon is not None:
                float(self.user_lat)
                float(self.user_lon)
            else:
                # Fallback a HA si no hay coordenadas
                self.user_lat = self.hass.config.latitude
                self.user_lon = self.hass.config.longitude
        except (ValueError, TypeError):
            _LOGGER.error("Coordenadas no válidas, usando fallback HA")
            self.user_lat = self.hass.config.latitude
            self.user_lon = self.hass.config.longitude

        # Último fallback a Madrid
        if self.user_lat is None or self.user_lon is None:
            self.user_lat = 40.4168
            self.user_lon = -3.7038
            _LOGGER.warning("Fallback a coordenadas de Madrid")

    async def _handle_person_change(self, event):
        """Manejar cambios en la entidad persona."""
        if self.config.get(CONF_LOCATION_MODE) != LOCATION_MODE_PERSON:
            return

        person = self.config.get(CONF_PERSON_ENTITY)
        state = self.hass.states.get(person)

        # Si la persona pierde GPS / queda unavailable
        if not state or state.attributes.get("latitude") is None:
            _LOGGER.warning(
                "Persona sin coordenadas, manteniendo última ubicación válida"
            )
            return

        _LOGGER.debug("Persona actualizada, refrescando coordenadas")

        self._update_coordinates_from_config()

        await self.coordinator.async_request_refresh()

    async def async_unload(self):
        """Limpiar listeners al descargar el módulo."""
        if hasattr(self, "_person_unsub"):
            self._person_unsub()

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
                name="dgt_incidents",
                update_method=self._async_update_data,
                update_interval=update_interval,
            )

            await self.coordinator.async_config_entry_first_refresh()

            if getattr(self, "person_entity", None):

                async def _person_updated(event):
                    new_state = event.data.get("new_state")
                    if new_state:
                        self.user_lat = new_state.attributes.get("latitude")
                        self.user_lon = new_state.attributes.get("longitude")
                        self.hass.async_create_task(
                            self.coordinator.async_request_refresh()
                        )

                self._person_unsub = async_track_state_change_event(
                    self.hass,
                    [self.person_entity],
                    _person_updated,
                )
            # escuchar cambios en modo PERSON
            if self.config.get(CONF_LOCATION_MODE) == LOCATION_MODE_PERSON:
                person = self.config.get(CONF_PERSON_ENTITY)
                if person:
                    self._person_unsub = async_track_state_change_event(
                        self.hass,
                        [person],
                        self._handle_person_change,
                    )
                    _LOGGER.info("Escuchando cambios en persona: %s", person)

            self.enabled = True
            _LOGGER.info("Módulo de incidencias DGT configurado")
            return True

        except Exception as err:
            _LOGGER.error("Error configurando módulo incidencias: %s", err)
            return False

    async def _async_update_data(self) -> Dict[str, Any]:
        """Actualizar datos."""
        # Actualizar coordenadas persona
        self._update_coordinates_from_config()

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

        severity_order = {"high": 3, "medium": 2, "low": 1, "unknown": 0}
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
