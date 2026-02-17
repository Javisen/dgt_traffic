"""
Módulo de electrolineras DGT (charging stations).
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
from ..api.charging_client import DGTChargingClient
from ..const import (
    DOMAIN,
    CONF_CHARGING_RADIUS_KM,
    CONF_SHOW_ONLY_AVAILABLE,
    CONF_CUSTOM_LATITUDE,
    CONF_CUSTOM_LONGITUDE,
    CONF_LOCATION_MODE,
    CONF_PERSON_ENTITY,
    LOCATION_MODE_HA,
    LOCATION_MODE_CUSTOM,
    LOCATION_MODE_PERSON,
    DEFAULT_CHARGING_RADIUS_KM,
    DEFAULT_SHOW_ONLY_AVAILABLE,
)

_LOGGER = logging.getLogger(__name__)


class DGTChargingModule(DGTModule):
    """Módulo para electrolineras DGT."""

    def __init__(self, hass: HomeAssistant, config: Dict[str, Any]):
        """Initialize charging module."""
        super().__init__(hass, config)
        self.name = "charging"
        self.client = None
        self._location_listener = None

        # Inicializar coordenadas según modo
        self._update_coordinates_from_config()

        # === CONFIGURACIÓN ESPECÍFICA DE CHARGING ===
        self.radius_km = config.get(CONF_CHARGING_RADIUS_KM, DEFAULT_CHARGING_RADIUS_KM)
        self.show_only_available = config.get(
            CONF_SHOW_ONLY_AVAILABLE, DEFAULT_SHOW_ONLY_AVAILABLE
        )

        # Intervalo de actualización (más largo que incidencias)
        self.update_interval_minutes = 30

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

        # Forzar actualización del coordinador
        await self.coordinator.async_request_refresh()

    async def async_setup(self) -> bool:
        """Configurar módulo."""
        try:
            from homeassistant.helpers.aiohttp_client import async_get_clientsession
            from homeassistant.helpers.event import async_track_state_change_event

            session = async_get_clientsession(self.hass)
            self.client = DGTChargingClient(session)

            update_interval = timedelta(minutes=self.update_interval_minutes)

            self.coordinator = DataUpdateCoordinator(
                self.hass,
                _LOGGER,
                name="dgt_charging",
                update_method=self._async_update_data,
                update_interval=update_interval,
            )

            await self.coordinator.async_config_entry_first_refresh()

            # Si estamos en modo PERSON, escuchar cambios
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
            _LOGGER.info("Módulo de electrolineras DGT configurado")
            return True

        except Exception as err:
            _LOGGER.error("Error configurando módulo electrolineras: %s", err)
            return False

    async def async_unload(self):
        """Limpiar listeners al descargar el módulo."""
        if hasattr(self, "_location_listener"):
            self._location_listener()

    async def _async_update_data(self) -> Dict[str, Any]:
        """Actualizar datos de electrolineras."""
        # Actualizar coordenadas persona
        self._update_coordinates_from_config()

        coordinates_valid = (
            self.user_lat is not None
            and self.user_lon is not None
            and isinstance(self.user_lat, (int, float))
            and isinstance(self.user_lon, (int, float))
            and -90 <= self.user_lat <= 90
            and -180 <= self.user_lon <= 180
        )

        if not coordinates_valid:
            _LOGGER.error("Coordenadas inválidas para filtrado")
            filter_active = False
        else:
            filter_active = True
            _LOGGER.debug("Usando coordenadas: %s, %s", self.user_lat, self.user_lon)

        try:
            if filter_active:
                all_stations = await self.client.get_charging_stations(
                    max_age_hours=24,
                    only_available=self.show_only_available,
                    user_lat=self.user_lat,
                    user_lon=self.user_lon,
                    radius_km=self.radius_km,
                )
            else:
                all_stations = await self.client.get_charging_stations(
                    max_age_hours=24,
                    only_available=self.show_only_available,
                )

            if not all_stations:
                _LOGGER.warning("No se obtuvieron estaciones del cliente")
                return {
                    "all_stations": [],
                    "nearby_stations": [],
                    "stations_by_operator": {},
                    "stations_by_power": {},
                    "stations_by_availability": {},
                    "statistics": {"total": 0, "nearby": 0},
                    "last_update": dt_util.utcnow().isoformat(),
                    "user_location": {
                        "latitude": self.user_lat,
                        "longitude": self.user_lon,
                        "radius_km": self.radius_km,
                    },
                }

            nearby_stations = []
            stations_by_operator = defaultdict(list)
            stations_by_power = defaultdict(list)
            stations_by_availability = defaultdict(list)

            total_power = 0
            total_available_points = 0

            for station in all_stations:
                if coordinates_valid:
                    distance = self._calculate_distance(station)
                    station["distance_km"] = distance
                    station["is_nearby"] = distance <= self.radius_km

                    if distance <= self.radius_km:
                        nearby_stations.append(station)
                    else:
                        continue
                else:
                    station["distance_km"] = 0
                    station["is_nearby"] = True
                    nearby_stations.append(station)

                operator_name = station.get("operator", {}).get("name", "Desconocido")
                stations_by_operator[operator_name].append(station)

                max_power = self._get_max_power(station)
                power_range = self._get_power_range(max_power)
                stations_by_power[power_range].append(station)

                status = (
                    "disponible"
                    if station.get("is_available", True)
                    else "no disponible"
                )
                stations_by_availability[status].append(station)

                total_power += max_power
                total_available_points += station.get("available_points", 0)

            if coordinates_valid:
                nearby_stations.sort(key=lambda x: x.get("distance_km", 999))

            stats = self._prepare_statistics(
                all_stations,
                nearby_stations,
                dict(stations_by_operator),
                dict(stations_by_power),
                dict(stations_by_availability),
                total_power,
                total_available_points,
            )

            _LOGGER.info(
                "Datos electrolineras actualizados: %s total, %s cercanas",
                len(all_stations),
                len(nearby_stations),
            )

            if filter_active and len(nearby_stations) == 0:
                _LOGGER.warning(
                    "Filtro activo pero cero estaciones cercanas. ¿Radio muy pequeño? (%s km)",
                    self.radius_km,
                )

            return {
                "all_stations": all_stations,
                "nearby_stations": nearby_stations,
                "stations_by_operator": dict(stations_by_operator),
                "stations_by_power": dict(stations_by_power),
                "stations_by_availability": dict(stations_by_availability),
                "statistics": stats,
                "last_update": dt_util.utcnow().isoformat(),
                "user_location": {
                    "latitude": self.user_lat,
                    "longitude": self.user_lon,
                    "radius_km": self.radius_km,
                },
            }

        except Exception as err:
            _LOGGER.error("Error actualizando datos electrolineras: %s", err)
            return {
                "all_stations": [],
                "nearby_stations": [],
                "stations_by_operator": {},
                "stations_by_power": {},
                "stations_by_availability": {},
                "statistics": {"total": 0, "nearby": 0},
                "last_update": dt_util.utcnow().isoformat(),
                "user_location": {
                    "latitude": self.user_lat,
                    "longitude": self.user_lon,
                    "radius_km": self.radius_km,
                },
            }

    def _calculate_distance(self, station: Dict) -> float:
        """Calcular distancia desde usuario a electrolinera en km."""
        try:
            station_lat = station.get("coordinates", {}).get("latitude")
            station_lon = station.get("coordinates", {}).get("longitude")

            if not station_lat or not station_lon:
                return 999.0

            user_coords = (self.user_lat, self.user_lon)
            station_coords = (float(station_lat), float(station_lon))

            return geodesic(user_coords, station_coords).kilometers
        except Exception:
            return 999.0

    def _get_max_power(self, station: Dict) -> float:
        """Obtener potencia máxima de los puntos de carga."""
        max_power = 0

        for point in station.get("charging_points", []):
            power = point.get("power_kw", 0)
            if power > max_power:
                max_power = power

        if max_power == 0:
            max_power = station.get("max_power_kw", 0)

        if max_power == 0:
            connector_type = station.get("connector_type", "").lower()
            if "ccs" in connector_type or "combo" in connector_type:
                max_power = 150
            elif "chademo" in connector_type:
                max_power = 50
            elif "type2" in connector_type or "iec62196" in connector_type:
                max_power = 22
            else:
                max_power = 11

        return max_power

    def _get_power_range(self, power_kw: float) -> str:
        """Clasificar potencia en rangos."""
        if power_kw >= 150:
            return "Ultra rápida (150+ kW)"
        elif 50 <= power_kw < 150:
            return "Rápida (50-149 kW)"
        elif 22 <= power_kw < 50:
            return "Semi-rápida (22-49 kW)"
        elif 0 < power_kw < 22:
            return "Lenta (< 22 kW)"
        else:
            return "Desconocida"

    def _prepare_statistics(
        self,
        all_stations,
        nearby_stations,
        stations_by_operator,
        stations_by_power,
        stations_by_availability,
        total_power,
        total_available_points,
    ) -> Dict[str, Any]:
        """Preparar estadísticas."""
        stats = {
            "total": len(all_stations),
            "nearby": len(nearby_stations),
            "by_operator": {},
            "by_power": {},
            "by_availability": {},
            "total_power_kw": round(total_power, 1),
            "total_available_points": total_available_points,
            "avg_power_per_station": round(
                total_power / len(nearby_stations) if nearby_stations else 0, 1
            ),
            "closest": None,
            "most_powerful": None,
        }

        for operator, stations in stations_by_operator.items():
            stats["by_operator"][operator] = len(stations)

        for power_range, stations in stations_by_power.items():
            stats["by_power"][power_range] = len(stations)

        for availability, stations in stations_by_availability.items():
            stats["by_availability"][availability] = len(stations)

        if nearby_stations:
            closest = min(nearby_stations, key=lambda x: x.get("distance_km", 999))
            stats["closest"] = {
                "name": closest.get("name", ""),
                "distance_km": closest.get("distance_km", 0),
                "operator": closest.get("operator", {}).get("name", ""),
                "available_points": closest.get("available_points", 0),
                "total_points": closest.get("total_points", 0),
            }

        if nearby_stations:
            most_powerful = max(nearby_stations, key=lambda x: self._get_max_power(x))
            stats["most_powerful"] = {
                "name": most_powerful.get("name", ""),
                "max_power_kw": self._get_max_power(most_powerful),
                "operator": most_powerful.get("operator", {}).get("name", ""),
                "distance_km": most_powerful.get("distance_km", 0),
            }

        return stats

    @property
    def data(self) -> Dict[str, Any]:
        """Acceso a datos del coordinador."""
        return (
            self.coordinator.data if self.coordinator and self.coordinator.data else {}
        )

    @property
    def nearby_stations(self) -> List[Dict]:
        """Electrolineras cercanas."""
        return self.data.get("nearby_stations", [])

    @property
    def stations_by_operator(self) -> Dict[str, List]:
        """Electrolineras agrupadas por operador."""
        return self.data.get("stations_by_operator", {})

    @property
    def device_info(self):
        """Return device information for Home Assistant."""
        return {
            "identifiers": {(DOMAIN, f"dgt_traffic_{self.name}")},
            "name": "DGT Electrolineras",
            "manufacturer": "DGT España",
            "model": "Datex2 v3 Energy",
            "configuration_url": "https://infocar.dgt.es",
            "entry_type": "service",
        }
