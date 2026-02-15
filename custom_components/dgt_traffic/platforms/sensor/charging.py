"""Sensor platform for DGT Charging Stations."""

import logging
import traceback
from typing import Dict, List, Any
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo

from ...const import DOMAIN

_STATION_ENTITIES = {}

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up DGT charging sensors con estructura de dispositivo."""
    _LOGGER.info("Iniciando setup de sensores de electrolineras")

    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    charging_module = entry_data.get("modules", {}).get("charging")

    if not charging_module:
        _LOGGER.error("No se encontró el módulo 'charging' en hass.data")
        return
    from homeassistant.helpers.device_registry import async_get

    device_registry = async_get(hass)

    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, f"{entry.entry_id}_charging")},
        name="DGT Electrolineras",
        manufacturer="DGT",
        model="Módulo de Carga Eléctrica",
    )

    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, f"{entry.entry_id}_stations")},
        name="Estaciones",
        manufacturer="DGT",
        model="Electrolineras dentro del radio",
        via_device=(DOMAIN, f"{entry.entry_id}_charging"),
    )
    try:
        sensors = [
            # Totales
            DGTTotalStationsSensor(charging_module, entry),
            DGTNearbyStationsSensor(charging_module, entry),
            DGTTotalAvailablePointsSensor(charging_module, entry),
            DGTTotalPowerSensor(charging_module, entry),
            # Más cercana
            DGTClosestStationSensor(charging_module, entry),
            # Por potencia
            DGTPowerRangeSensor(
                charging_module,
                entry,
                "Ultra rápida (150+ kW)",
                "Estaciones Ultra Rápidas",
            ),
            DGTPowerRangeSensor(
                charging_module, entry, "Rápida (50-149 kW)", "Estaciones Rápidas"
            ),
            DGTPowerRangeSensor(
                charging_module,
                entry,
                "Semi-rápida (22-49 kW)",
                "Estaciones Semi-rápidas",
            ),
            DGTPowerRangeSensor(
                charging_module, entry, "Lenta (< 22 kW)", "Estaciones Lentas"
            ),
            # Lista de estaciones
            DGTAllStationsSensor(charging_module, entry),
            # Potencia promedio
            DGTAvgPowerSensor(charging_module, entry),
        ]

        _LOGGER.info("Registrando %s entidades en el Hub de Carga", len(sensors))
        async_add_entities(sensors, update_before_add=True)

        manager = DGTChargingStationManager(
            hass, entry, charging_module, async_add_entities
        )
        await manager.async_init()

    except Exception as err:
        _LOGGER.error("Error crítico en setup de sensores: %s", err)


class DGTBaseChargingSensor(SensorEntity):
    """Base class for DGT charging sensors con Device Info."""

    def __init__(self, module, entry):
        self.module = module
        self.entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        """Configuración del Hub de Electrolineras."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.entry.entry_id}_charging")},
            name="DGT Electrolineras",
            manufacturer="DGT",
            model="Módulo de Carga Eléctrica",
            configuration_url="https://infocar.dgt.es",
        )

    @property
    def should_poll(self) -> bool:
        return False

    async def async_added_to_hass(self):
        """Register callbacks."""
        self.async_on_remove(
            self.module.async_add_listener(self._handle_coordinator_update)
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


class DGTTotalStationsSensor(DGTBaseChargingSensor):
    """Sensor for total charging stations."""

    def __init__(self, module, entry):
        super().__init__(module, entry)
        self._attr_name = "DGT Electrolineras Totales"
        self._attr_unique_id = f"{entry.entry_id}_chg_total_stations"
        self._attr_icon = "mdi:ev-station"
        self._attr_native_unit_of_measurement = "estaciones"

    @property
    def native_value(self):
        data = self.module.data or {}
        stats = data.get("statistics", {})
        return stats.get("total", 0)

    @property
    def extra_state_attributes(self):
        data = self.module.data or {}
        stats = data.get("statistics", {})

        por_operador_texto = "\n".join(
            f"{op}: {count}" for op, count in stats.get("by_operator", {}).items()
        )

        por_potencia_texto = "\n".join(
            f"{rango}: {count}" for rango, count in stats.get("by_power", {}).items()
        )

        attributes = {
            "última_actualización": data.get("last_update"),
            "cercanas": stats.get("nearby", 0),
            "por_operador": por_operador_texto,
            "por_potencia": por_potencia_texto,
            "puntos_disponibles": stats.get("total_available_points", 0),
            "potencia_total_kw": stats.get("total_power_kw", 0),
            "radio_usuario_km": getattr(self.module, "radius_km", "desconocido"),
        }

        closest = stats.get("closest")
        if closest:
            attributes.update(
                {
                    "más_cercana_nombre": closest.get("name"),
                    "más_cercana_distancia_km": closest.get("distance_km"),
                    "más_cercana_operador": closest.get("operator"),
                    "más_cercana_puntos_disponibles": closest.get("available_points"),
                }
            )

        return attributes


class DGTNearbyStationsSensor(DGTBaseChargingSensor):
    """Sensor for nearby charging stations."""

    def __init__(self, module, entry):
        super().__init__(module, entry)
        self._attr_name = "DGT Electrolineras Cercanas"
        self._attr_unique_id = f"{entry.entry_id}_chg_nearby_stations"
        self._attr_icon = "mdi:map-marker-radius"
        self._attr_native_unit_of_measurement = "estaciones"

    @property
    def native_value(self):
        data = self.module.data or {}
        stats = data.get("statistics", {})
        return stats.get("nearby", 0)

    @property
    def extra_state_attributes(self):
        stations = self.module.nearby_stations or []

        attributes = {
            "estaciones_cercanas": len(stations),
            "última_actualización": (
                self.module.data.get("last_update") if self.module.data else None
            ),
        }

        if stations:
            texto = "\n\n".join(
                [
                    "\n".join(
                        [
                            f"nombre: {s.get('name', '')}",
                            f"distancia_km: {round(s.get('distance_km', 0), 1)}",
                            f"operador: {s.get('operator', {}).get('name', '')}",
                            f"puntos_disponibles: {s.get('available_points', 0)}",
                            f"potencia_máxima_kw: {self._get_max_power(s)}",
                        ]
                    )
                    for s in stations[:5]
                ]
            )

            attributes["estaciones"] = texto

        return attributes

    def _get_max_power(self, station: Dict) -> float:
        max_power = 0
        for point in station.get("charging_points", []):
            power = point.get("power_kw", 0)
            if power > max_power:
                max_power = power
        return max_power


class DGTTotalAvailablePointsSensor(DGTBaseChargingSensor):
    """Sensor for total available charging points."""

    def __init__(self, module, entry):
        super().__init__(module, entry)
        self._attr_name = "DGT Puntos de Carga Disponibles"
        self._attr_unique_id = f"{entry.entry_id}_chg_available_points"
        self._attr_icon = "mdi:ev-plug-type2"
        self._attr_native_unit_of_measurement = "puntos"

    @property
    def native_value(self):
        data = self.module.data or {}
        stats = data.get("statistics", {})
        return stats.get("total_available_points", 0)


class DGTTotalPowerSensor(DGTBaseChargingSensor):
    """Sensor for total power capacity."""

    def __init__(self, module, entry):
        super().__init__(module, entry)
        self._attr_name = "DGT Potencia Total Cercana"
        self._attr_unique_id = f"{entry.entry_id}_chg_total_power"
        self._attr_icon = "mdi:lightning-bolt"
        self._attr_native_unit_of_measurement = "kW"

    @property
    def native_value(self):
        data = self.module.data or {}
        stats = data.get("statistics", {})
        return stats.get("total_power_kw", 0)


class DGTClosestStationSensor(DGTBaseChargingSensor):
    """Sensor for closest charging station."""

    def __init__(self, module, entry):
        super().__init__(module, entry)
        self._attr_name = "DGT Electrolinera Más Cercana"
        self._attr_unique_id = f"{entry.entry_id}_chg_closest_station"
        self._attr_icon = "mdi:map-marker-distance"
        self._attr_native_unit_of_measurement = "km"

    def _clean_address(self, address: str) -> str:
        """Devuelve dirección + municipio, eliminando provincia y comunidad."""
        if not address:
            return "No disponible"

        for corte in ["Provincia:", "Comunidad Autónoma:"]:
            if corte in address:
                address = address.split(corte)[0].strip().rstrip(",")

        address = address.replace("Dirección:", "").strip()
        partes = [p.strip() for p in address.split(",") if p.strip()]

        direccion = []
        municipio = None

        for p in partes:
            if p.startswith("Municipio:"):
                municipio = p.replace("Municipio:", "").strip()
            else:
                direccion.append(p)

        if municipio:
            return f"{', '.join(direccion)}, {municipio}"

        return ", ".join(direccion)

    @property
    def native_value(self):
        stations = self.module.nearby_stations or []
        if not stations:
            return 0
        closest = min(stations, key=lambda x: x.get("distance_km", 999))
        return round(closest.get("distance_km", 0), 1)

    @property
    def extra_state_attributes(self):
        stations = self.module.nearby_stations or []
        if not stations:
            return {"mensaje": "No hay electrolineras cercanas"}

        closest = min(stations, key=lambda x: x.get("distance_km", 999))

        return {
            "nombre": closest.get("name", "Desconocido"),
            "operador": closest.get("operator", {}).get("name", "Desconocido"),
            "dirección": self._clean_address(closest.get("address", "")),
            "puntos_disponibles": closest.get("available_points", 0),
            "distancia_km": round(closest.get("distance_km", 0), 1),
            "coordenadas": closest.get("coordinates", {}),
        }


class DGTPowerRangeSensor(DGTBaseChargingSensor):
    """Sensor for stations by power range with detailed attributes."""

    def __init__(self, module, entry, power_range, name):
        super().__init__(module, entry)
        self.power_range = power_range
        clean_range = power_range.split()[0].lower()
        self._attr_name = f"DGT {name}"
        self._attr_unique_id = f"{entry.entry_id}_chg_pwr_{clean_range}"
        self._attr_icon = "mdi:speedometer"
        self._attr_native_unit_of_measurement = "estaciones"

    @property
    def native_value(self):
        data = self.module.data or {}
        by_power = data.get("stations_by_power", {})
        return len(by_power.get(self.power_range, []))

    @property
    def extra_state_attributes(self):
        """Return detailed attributes for stations in this power range."""
        data = self.module.data or {}
        all_stations = data.get("nearby_stations", [])

        if not all_stations:
            return {"info": "Sin datos disponibles"}

        stations_in_range = [
            station
            for station in all_stations
            if station.get("power_range") == self.power_range
        ]

        if not stations_in_range:
            return {
                "estaciones_en_rango": 0,
                "rango": self.power_range,
                "mensaje": f"No hay estaciones en {self.power_range}",
            }

        total_power = sum(s.get("max_power_kw", 0) for s in stations_in_range)
        avg_power = round(total_power / len(stations_in_range), 1)

        operators = {}
        for station in stations_in_range:
            operator_name = station.get("operator", {}).get("name", "Desconocido")
            operators[operator_name] = operators.get(operator_name, 0) + 1

        top_stations = []
        sorted_by_distance = sorted(
            stations_in_range, key=lambda x: x.get("distance_km", 999)
        )
        for station in sorted_by_distance[:5]:
            top_stations.append(
                {
                    "nombre": station.get("name", "Sin nombre")[:30],
                    "operador": station.get("operator", {}).get("name", "Desconocido"),
                    "distancia_km": round(station.get("distance_km", 0), 1),
                    "potencia_kw": station.get("max_power_kw", 0),
                    "puntos": f"{station.get('available_points', 0)}/{station.get('total_points', 0)}",
                    "direccion": self._shorten_address(station.get("address", "")),
                }
            )

        estaciones_texto = "\n\n".join(
            [
                "\n".join(
                    [
                        f"nombre: {s['nombre']}",
                        f"distancia_km: {s['distancia_km']}",
                        f"operador: {s['operador']}",
                        f"puntos: {s['puntos']}",
                        f"potencia_kw: {s['potencia_kw']}",
                        f"direccion: {s['direccion']}",
                    ]
                )
                for s in top_stations
            ]
        )

        locations = self._extract_main_locations(stations_in_range)

        return {
            "estaciones_totales": len(stations_in_range),
            "rango_potencia": self.power_range,
            "potencia_promedio_kw": avg_power,
            "operadores": dict(
                sorted(operators.items(), key=lambda x: x[1], reverse=True)
            ),
            "ubicaciones_principales": locations[:3],
            "estaciones_cercanas": estaciones_texto,
            "puntos_carga_totales": sum(
                s.get("total_points", 0) for s in stations_in_range
            ),
            "puntos_disponibles": sum(
                s.get("available_points", 0) for s in stations_in_range
            ),
            "radio_busqueda_km": getattr(self.module, "radius_km", 50),
        }

    def _shorten_address(self, address: str, max_length: int = 40) -> str:

        if not address or address == "Dirección no disponible":
            return "No disponible"
        if len(address) <= max_length:
            return address
        return address[: max_length - 3] + "..."

    def _extract_main_locations(self, stations: List[Dict]) -> List[Dict]:
        """Extraer las ubicaciones principales donde hay estaciones."""
        from collections import defaultdict

        location_count = defaultdict(int)

        for station in stations:
            address = station.get("address", "")
            location = self._extract_location_from_address(address)
            location_count[location] += 1

        locations = [
            {"ubicacion": loc, "estaciones": count}
            for loc, count in location_count.items()
        ]

        return sorted(locations, key=lambda x: x["estaciones"], reverse=True)

    def _extract_location_from_address(self, address: str) -> str:
        """Intentar extraer municipio/provincia de la dirección."""
        if not address or address == "Dirección no disponible":
            return "Desconocido"

        if "Municipio:" in address:
            try:
                import re

                match = re.search(r"Municipio:\s*([^,]+)", address)
                if match:
                    return match.group(1).strip().title()
            except:
                pass

        if "Provincia:" in address:
            try:
                import re

                match = re.search(r"Provincia:\s*([^,]+)", address)
                if match:
                    return match.group(1).strip().title()
            except:
                pass

        import re

        postal_code = re.search(r"\b\d{5}\b", address)
        if postal_code:
            return f"C.P. {postal_code.group()}"

        if "," in address:
            first_part = address.split(",")[0].strip()
            if first_part and len(first_part) > 5:
                return first_part[:30]

        words = address.split()
        if len(words) >= 2:
            return f"{words[0]} {words[1]}"

        return "Ubicación no especificada"


class DGTAllStationsSensor(DGTBaseChargingSensor):
    """Sensor with list of all stations."""

    def __init__(self, module, entry):
        super().__init__(module, entry)
        self._attr_name = "DGT Todas las Electrolineras"
        self._attr_unique_id = f"{entry.entry_id}_chg_all_list"
        self._attr_icon = "mdi:clipboard-list"

    @property
    def native_value(self):
        return len(self.module.nearby_stations or [])

    @property
    def extra_state_attributes(self):
        stations = self.module.nearby_stations or []

        estaciones_texto = "\n\n".join(
            [
                "\n".join(
                    [
                        f"nombre: {s.get('name', '')}",
                        f"distancia_km: {round(s.get('distance_km', 0), 2)}",
                        f"puntos_disponibles: {s.get('available_points', 0)}",
                    ]
                )
                for s in stations[:15]
            ]
        )

        return {
            "total": len(stations),
            "estaciones": estaciones_texto,
        }


class DGTAvgPowerSensor(DGTBaseChargingSensor):
    """Sensor for average power per station."""

    def __init__(self, module, entry):
        super().__init__(module, entry)
        self._attr_name = "DGT Potencia Promedio"
        self._attr_unique_id = f"{entry.entry_id}_chg_avg_power"
        self._attr_icon = "mdi:calculator"
        self._attr_native_unit_of_measurement = "kW"

    @property
    def native_value(self):
        stats = (self.module.data or {}).get("statistics", {})
        return stats.get("avg_power_per_station", 0)


from homeassistant.helpers.entity import DeviceInfo
from ...const import DOMAIN


class DGTChargingStationSensor(DGTBaseChargingSensor):

    def __init__(self, module, entry, station):
        super().__init__(module, entry)
        self.station = station
        self.entry = entry

        sid = station.get("id")

        self._attr_unique_id = f"{entry.entry_id}_station_{sid}"

        # Nombre más humano
        raw_name = station.get("name", "").strip()
        operator = station.get("operator", {}).get("name", "")
        distance = round(station.get("distance_km", 0), 1)

        if raw_name.lower().startswith("estación") or raw_name.isalnum():
            if operator:
                name = f"{operator} ({distance} km)"
            else:
                name = f"Electrolinera ({distance} km)"
        else:
            name = raw_name

        self._attr_name = f"DGT {name}"

        # Coordenadas
        coords = station.get("coordinates", {})
        self._attr_latitude = coords.get("latitude")
        self._attr_longitude = coords.get("longitude")

        max_power = station.get("max_power_kw", 0)

        if max_power >= 150:
            self._attr_icon = "mdi:flash"
        elif max_power >= 50:
            self._attr_icon = "mdi:lightning-bolt-circle"
        else:
            self._attr_icon = "mdi:ev-plug-type2"

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.entry.entry_id}_stations")},
        )

    @property
    def native_value(self):
        return self.station.get("available_points", 0)

    @property
    def extra_state_attributes(self):
        coords = self.station.get("coordinates", {})

        return {
            "distance_km": round(self.station.get("distance_km", 0), 2),
            "operator": self.station.get("operator", {}).get("name"),
            "total_points": self.station.get("total_points"),
            "available_points": self.station.get("available_points"),
            "max_power_kw": self.station.get("max_power_kw"),
            "power_range": self.station.get("power_range"),
            "latitude": coords.get("latitude"),
            "longitude": coords.get("longitude"),
            "charging_points": self.station.get("charging_points", []),
        }


class DGTChargingStationManager:

    def __init__(self, hass, entry, module, async_add):
        self.hass = hass
        self.entry = entry
        self.module = module
        self.async_add = async_add
        self.entities = {}

    async def async_init(self):
        self.module.async_add_listener(self._schedule_update)
        await self._update()

    @callback
    def _schedule_update(self):
        self.hass.async_create_task(self._update())

    async def _update(self):
        stations = self.module.nearby_stations or []
        current_ids = set(s["id"] for s in stations)
        existing_ids = set(self.entities.keys())

        for station in stations:
            sid = station["id"]

            if sid in self.entities:
                self.entities[sid].station = station
                self.entities[sid].async_write_ha_state()
            else:
                ent = DGTChargingStationSensor(self.module, self.entry, station)
                self.entities[sid] = ent
                self.async_add([ent])

        for sid in existing_ids - current_ids:
            ent = self.entities.pop(sid)
            await ent.async_remove()
