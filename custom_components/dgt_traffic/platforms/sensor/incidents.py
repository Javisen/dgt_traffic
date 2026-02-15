"""Plataforma de sensores para DGT Tráfico - Módulo de Incidencias."""

import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.util import dt as dt_util

from ...const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Configuración de sensores de incidencias con filtro de instancia."""
    from ...const import CONF_ENABLE_INCIDENTS

    if not entry.data.get(CONF_ENABLE_INCIDENTS, False):
        _LOGGER.debug("Saltando: Esta instancia no es de incidencias")
        return

    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    incidents_module = entry_data.get("modules", {}).get("incidents")

    if not incidents_module:
        _LOGGER.debug("Módulo no listo en hass.data (esperando init)")
        return

    try:
        sensors = [
            DGTTotalIncidentsSensor(incidents_module, entry),
            DGTIncidentsByTypeSensor(
                incidents_module, entry, "weather", "Meteorológicas"
            ),
            DGTIncidentsByTypeSensor(incidents_module, entry, "roadworks", "Obras"),
            DGTIncidentsByTypeSensor(incidents_module, entry, "accident", "Accidentes"),
            DGTIncidentsByTypeSensor(
                incidents_module, entry, "obstruction", "Obstáculos"
            ),
            DGTIncidentsByTypeSensor(
                incidents_module, entry, "congestion", "Congestiones"
            ),
            DGTIncidentsByTypeSensor(
                incidents_module, entry, "restriction", "Restricciones"
            ),
            DGTIncidentsByTypeSensor(
                incidents_module, entry, "information", "Informaciones"
            ),
            DGTIncidentsByTypeSensor(incidents_module, entry, "other", "Otras"),
            DGTNearestIncidentSensor(incidents_module, entry),
            DGTAllIncidentsSensor(incidents_module, entry),
            DGTIncidentsBySeveritySensor(
                incidents_module, entry, "high", "Alta Severidad"
            ),
            DGTIncidentsBySeveritySensor(
                incidents_module, entry, "medium", "Media Severidad"
            ),
            DGTIncidentsBySeveritySensor(
                incidents_module, entry, "low", "Baja Severidad"
            ),
        ]

        _LOGGER.info("Registrando %s entidades en el Hub de Incidencias", len(sensors))
        async_add_entities(sensors, update_before_add=True)

    except Exception as err:
        _LOGGER.error("Error crítico al instanciar sensores: %s", err)


class DGTBaseSensor(SensorEntity):
    """Clase base para sensores DGT con Device Info tipo Hub."""

    TYPE_TRANSLATION = {
        "weather": "Meteorológicas",
        "roadworks": "Obras",
        "accident": "Accidentes",
        "obstruction": "Obstáculos",
        "congestion": "Congestiones",
        "restriction": "Restricciones",
        "information": "Informaciones",
        "other": "Otras",
        "high": "Alta",
        "medium": "Media",
        "low": "Baja",
        "unknown": "Sin clasificar",
    }

    def __init__(self, module, entry):
        self.module = module
        self.entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        """Configuración del Hub de Incidencias."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.entry.entry_id}_incidents")},
            name="DGT Incidencias",
            manufacturer="DGT",
            model="Módulo de Tráfico en Tiempo Real",
            configuration_url="https://infocar.dgt.es",
        )

    @property
    def should_poll(self) -> bool:
        return False

    async def async_added_to_hass(self):
        """Registrar callbacks."""
        self.async_on_remove(
            self.module.async_add_listener(self._handle_coordinator_update)
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    def _translate_type(self, inc_type):
        return self.TYPE_TRANSLATION.get(inc_type, inc_type)

    def _format_datetime(self, dt_string):
        if not dt_string:
            return None
        try:
            dt = dt_util.parse_datetime(dt_string)
            if dt:
                return dt_util.as_local(dt).strftime("%d/%m/%Y, %H:%M:%S")
        except (ValueError, TypeError):
            pass
        return dt_string

    def _format_incident_list(self, incidents, max_items=5):
        if not incidents:
            return "Sin incidencias"

        formatted = []
        for inc in incidents[:max_items]:
            desc = inc.get("description", "Sin descripción")
            if len(desc) > 60:
                desc = desc[:57] + "..."

            dist = round(inc.get("distance_km", 0), 2)
            road = inc.get("road", "Desconocida")
            type_raw = inc.get("type", "other")
            inc_type = self._translate_type(type_raw)

            formatted.append(f"{desc} - {dist}km ({road}, {inc_type})")

        return "\n".join(formatted)


class DGTTotalIncidentsSensor(DGTBaseSensor):
    """Sensor para total de incidencias cercanas."""

    def __init__(self, module, entry):
        super().__init__(module, entry)
        self._attr_name = "DGT Incidencias Totales"
        self._attr_unique_id = f"{entry.entry_id}_inc_total_incidents"
        self._attr_icon = "mdi:car-info"
        self._attr_native_unit_of_measurement = "incidencias"

    def _format_stats_dict(self, stats_dict):
        if not stats_dict:
            return "Ninguna"

        parts = []
        for key, value in stats_dict.items():
            if value > 0:
                label = self._translate_type(key)
                parts.append(f"{label}: {value}")

        return " | ".join(parts) if parts else "Ninguna"

    @property
    def native_value(self):
        data = self.module.data or {}
        stats = data.get("statistics", {})
        return stats.get("nearby", 0)

    @property
    def extra_state_attributes(self):
        data = self.module.data or {}
        stats = data.get("statistics", {})

        attributes = {
            "Última Actualización": self._format_datetime(data.get("last_update")),
            "Total Nacional": stats.get("total", 0),
            "Por Tipo": self._format_stats_dict(stats.get("by_type", {})),
            "Por Severidad": self._format_stats_dict(stats.get("by_severity", {})),
            "Radio Usuario (km)": getattr(self.module, "radius_km", "desconocido"),
        }

        closest = stats.get("closest")
        if closest:
            dist_corta = round(closest.get("distance_km", 0), 2)
            attributes.update(
                {
                    "Incidente Más Cercano": f"{closest.get('description', 'Desconocido')} - {dist_corta}km",
                    "Incidente Cercano - Distancia (km)": dist_corta,
                    "Incidente Cercano - Tipo": self._translate_type(
                        closest.get("type")
                    ),
                    "Incidente Cercano - Severidad": self._translate_type(
                        closest.get("severity")
                    ),
                }
            )

        return attributes


class DGTIncidentsByTypeSensor(DGTBaseSensor):
    """Sensor para incidencias por tipo."""

    def __init__(self, module, entry, inc_type, name):
        super().__init__(module, entry)
        self.inc_type = inc_type
        self._attr_name = f"DGT {name}"
        self._attr_unique_id = f"{entry.entry_id}_inc_type_{inc_type}"
        self._attr_icon = self._get_icon(inc_type)
        self._attr_native_unit_of_measurement = "incidencias"

    def _get_icon(self, inc_type):
        icons = {
            "weather": "mdi:weather-snowy-rainy",
            "roadworks": "mdi:road",
            "accident": "mdi:car-connected",
            "obstruction": "mdi:alert-octagon",
            "congestion": "mdi:traffic-light",
            "restriction": "mdi:traffic-cone",
            "information": "mdi:information",
            "other": "mdi:alert",
        }
        return icons.get(inc_type, "mdi:car-emergency")

    @property
    def native_value(self):
        incidents = self.module.incidents_by_type.get(self.inc_type, [])
        return len(incidents)

    @property
    def extra_state_attributes(self):
        incidents = self.module.incidents_by_type.get(self.inc_type, [])
        attributes = {
            "Total Incidencias": len(incidents),
            "Última Actualización": self._format_datetime(
                self.module.data.get("last_update") if self.module.data else None
            ),
        }

        if incidents:
            attributes["Incidencias"] = self._format_incident_list(incidents, 15)

            detalles_list = []
            for inc in incidents[:10]:
                desc = inc.get("description", "Sin descripción")
                tipo = self._translate_type(inc.get("type", ""))
                dist = round(inc.get("distance_km", 0), 2)
                carretera = inc.get("road", "N/A")
                sev = self._translate_type(inc.get("severity", ""))
                desc_raw = inc.get("description", "Sin descripción")
                desc_limpia = desc_raw.split(" - ")[0]

                linea = (
                    f"Tipo: {tipo}  \n"
                    f"Carretera: {carretera}  \n"
                    f"Distancia: {dist}km  \n"
                    f"Severidad: {sev}  \n"
                    f"Detalle: {desc_limpia}"
                )
                detalles_list.append(linea)

            attributes["Incidencias Detalladas"] = "\n\n---\n\n".join(detalles_list)

        return attributes


class DGTNearestIncidentSensor(DGTBaseSensor):
    """Sensor para la incidencia más cercana."""

    def __init__(self, module, entry):
        super().__init__(module, entry)
        self._attr_name = "DGT Incidencia Más Cercana"
        self._attr_unique_id = f"{entry.entry_id}_inc_nearest_incident"
        self._attr_icon = "mdi:map-marker-distance"
        self._attr_native_unit_of_measurement = "km"

    @property
    def native_value(self):
        incidents = self.module.nearby_incidents or []
        if not incidents:
            return 0
        nearest = min(incidents, key=lambda x: x.get("distance_km", 999))
        return round(nearest.get("distance_km", 0), 1)

    @property
    def extra_state_attributes(self):
        incidents = self.module.nearby_incidents or []
        if not incidents:
            return {"Mensaje": "Sin incidencias cercanas"}

        nearest = min(incidents, key=lambda x: x.get("distance_km", 999))

        descripcion = nearest.get("description", "Desconocido")
        if len(descripcion) > 80:
            descripcion = descripcion[:77] + "..."

        return {
            "Descripción": descripcion,
            "Tipo": nearest.get("type", "Desconocido"),
            "Severidad": nearest.get("severity", "Desconocida"),
            "Carretera": nearest.get("road", ""),
            "Distancia (km)": round(nearest.get("distance_km", 0), 1),
            "Causa": nearest.get("detailed_cause", nearest.get("cause_type", "")),
            "Última Actualización": self._format_datetime(
                self.module.data.get("last_update") if self.module.data else None
            ),
        }


class DGTAllIncidentsSensor(DGTBaseSensor):
    """Sensor con lista de todas las incidencias."""

    def __init__(self, module, entry):
        super().__init__(module, entry)
        self._attr_name = "DGT Todas las Incidencias"
        self._attr_unique_id = f"{entry.entry_id}_inc_all_incidents"
        self._attr_icon = "mdi:clipboard-list"
        self._attr_native_unit_of_measurement = "incidencias"

    @property
    def native_value(self):
        return len(self.module.nearby_incidents or [])

    @property
    def extra_state_attributes(self):
        incidents = self.module.nearby_incidents or []
        attributes = {
            "Total Incidencias": len(incidents),
            "Última Actualización": self._format_datetime(
                self.module.data.get("last_update") if self.module.data else None
            ),
        }

        if incidents:
            attributes["Incidencias"] = self._format_incident_list(incidents, 15)

            detalles_list = []
            for inc in incidents[:10]:
                desc = inc.get("description", "Sin descripción")
                tipo = self._translate_type(inc.get("type", ""))
                dist = round(inc.get("distance_km", 0), 2)
                carretera = inc.get("road", "")
                sev = self._translate_type(inc.get("severity", ""))

                linea = (
                    f"Tipo: {tipo}  \n"
                    f"Carretera: {carretera}  \n"
                    f"Distancia: {dist}km  \n"
                    f"Severidad: {sev}  \n"
                    f"Detalle: {desc}"
                )
                detalles_list.append(linea)

            attributes["Incidencias Detalladas"] = "\n\n".join(detalles_list)

        return attributes


class DGTIncidentsBySeveritySensor(DGTBaseSensor):
    """Sensor para incidencias por severidad."""

    def __init__(self, module, entry, severity, name):
        super().__init__(module, entry)
        self.severity = severity
        self._attr_name = f"DGT {name}"
        self._attr_unique_id = f"{entry.entry_id}_inc_severity_{severity}"
        self._attr_icon = self._get_icon(severity)
        self._attr_native_unit_of_measurement = "incidencias"

    def _get_icon(self, severity):
        icons = {
            "high": "mdi:alert-octagram",
            "medium": "mdi:alert",
            "low": "mdi:information",
        }
        return icons.get(severity, "mdi:alert")

    @property
    def native_value(self):
        incidents = self.module.incidents_by_severity.get(self.severity, [])
        return len(incidents)

    @property
    def extra_state_attributes(self):
        incidents = self.module.incidents_by_severity.get(self.severity, [])
        attributes = {
            "Total Incidencias": len(incidents),
            "Última Actualización": self._format_datetime(
                self.module.data.get("last_update") if self.module.data else None
            ),
        }

        if incidents:
            attributes["Incidencias"] = self._format_incident_list(incidents, 15)

            detalles_list = []
            for inc in incidents[:10]:
                desc = inc.get("description", "Sin descripción")
                tipo = self._translate_type(inc.get("type", ""))
                dist = round(inc.get("distance_km", 0), 2)
                carretera = inc.get("road", "N/A")
                sev = self._translate_type(self.severity)

                linea = (
                    f"Tipo: {tipo}  \n"
                    f"Carretera: {carretera}  \n"
                    f"Distancia: {dist}km  \n"
                    f"Severidad: {sev}  \n"
                    f"Detalle: {desc}"
                )
                detalles_list.append(linea)

            attributes["Incidencias Detalladas"] = "\n\n---\n\n".join(detalles_list)

        return attributes
