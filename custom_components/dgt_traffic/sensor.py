"""Sensor platform for DGT Traffic."""

import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import callback

from .const import DOMAIN, SENSOR_ENTITY_IDS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up DGT incident sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    sensors = [
        # Total incidents
        DGTTotalIncidentsSensor(coordinator, entry),
        # Incidents by type
        DGTIncidentsByTypeSensor(
            coordinator, entry, "weather", "Incidencias Meteorológicas"
        ),
        DGTIncidentsByTypeSensor(coordinator, entry, "roadworks", "Obras en Carretera"),
        DGTIncidentsByTypeSensor(coordinator, entry, "accident", "Accidentes"),
        DGTIncidentsByTypeSensor(coordinator, entry, "obstruction", "Obstáculos"),
        DGTIncidentsByTypeSensor(coordinator, entry, "congestion", "Congestiones"),
        DGTIncidentsByTypeSensor(coordinator, entry, "restriction", "Restricciones"),
        DGTIncidentsByTypeSensor(coordinator, entry, "information", "Informaciones"),
        DGTIncidentsByTypeSensor(coordinator, entry, "other", "Otras Incidencias"),
        # Nearest incident
        DGTNearestIncidentSensor(coordinator, entry),
        # All incidents list
        DGTAllIncidentsSensor(coordinator, entry),
        # Severity sensors
        DGTIncidentsBySeveritySensor(
            coordinator, entry, "high", "Incidencias Alta Severidad"
        ),
        DGTIncidentsBySeveritySensor(
            coordinator, entry, "medium", "Incidencias Media Severidad"
        ),
        DGTIncidentsBySeveritySensor(
            coordinator, entry, "low", "Incidencias Baja Severidad"
        ),
    ]

    async_add_entities(sensors, True)


class DGTTotalIncidentsSensor(SensorEntity):
    """Sensor for total nearby incidents."""

    def __init__(self, coordinator, entry):
        """Initialize."""
        self.coordinator = coordinator
        self.entry = entry

        self._attr_name = "DGT Incidentes Totales"
        self._attr_unique_id = f"{entry.entry_id}_total_incidents"
        self._attr_icon = "mdi:car-alert"
        self._attr_native_unit_of_measurement = "incidencias"

    @property
    def state(self):
        """Return total incidents count."""
        data = self.coordinator.data or {}
        stats = data.get("statistics", {})
        return stats.get("nearby", 0)

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        data = self.coordinator.data or {}
        stats = data.get("statistics", {})

        attributes = {
            "last_update": data.get("last_update"),
            "total_national": stats.get("total", 0),
            "by_type": stats.get("by_type", {}),
            "by_severity": stats.get("by_severity", {}),
            "user_radius_km": self.coordinator.radius_km,
        }

        # Add closest incident info
        closest = stats.get("closest")
        if closest:
            attributes.update(
                {
                    "closest_description": closest.get("description"),
                    "closest_distance_km": closest.get("distance_km"),
                    "closest_type": closest.get("type"),
                    "closest_severity": closest.get("severity"),
                }
            )

        # Add most severe incident info
        most_severe = stats.get("most_severe")
        if most_severe:
            attributes.update(
                {
                    "most_severe_description": most_severe.get("description"),
                    "most_severe_type": most_severe.get("type"),
                    "most_severe_severity": most_severe.get("severity"),
                }
            )

        return attributes


class DGTIncidentsByTypeSensor(SensorEntity):
    """Sensor for incidents by type."""

    def __init__(self, coordinator, entry, inc_type, name):
        """Initialize."""
        self.coordinator = coordinator
        self.entry = entry
        self.inc_type = inc_type

        self._attr_name = f"DGT {name}"
        self._attr_unique_id = f"{entry.entry_id}_incidents_{inc_type}"
        self._attr_icon = self._get_icon(inc_type)
        self._attr_native_unit_of_measurement = "incidencias"

    def _get_icon(self, inc_type):
        """Get icon for incident type."""
        icons = {
            "weather": "mdi:weather-snowy-rainy",
            "roadworks": "mdi:road",
            "accident": "mdi:car-crash",
            "obstruction": "mdi:alert-octagon",
            "congestion": "mdi:traffic-light",
            "restriction": "mdi:traffic-cone",
            "information": "mdi:information",
            "other": "mdi:alert",
        }
        return icons.get(inc_type, "mdi:alert")

    @property
    def state(self):
        """Return incidents count for this type."""
        data = self.coordinator.data or {}
        stats = data.get("statistics", {})
        by_type = stats.get("by_type", {})
        return by_type.get(self.inc_type, 0)

    @property
    def extra_state_attributes(self):
        """Return list of incidents for this type."""
        incidents = self.coordinator.incidents_by_type.get(self.inc_type, [])

        attributes = {
            "incidents_count": len(incidents),
            "last_update": (
                self.coordinator.data.get("last_update")
                if self.coordinator.data
                else None
            ),
        }

        # Add detailed incident info (limited to 5)
        if incidents:
            detailed = []
            for inc in incidents[:5]:  # Limit to 5
                detailed.append(
                    {
                        "description": inc.get("description", ""),
                        "distance_km": inc.get("distance_km", 0),
                        "severity": inc.get("severity", ""),
                        "road": inc.get("road", ""),
                        "km_from": inc.get("km_from"),
                        "km_to": inc.get("km_to"),
                        "province": inc.get("province"),
                        "creation_time": inc.get("creation_time"),
                    }
                )
            attributes["incidents"] = detailed

        return attributes


class DGTNearestIncidentSensor(SensorEntity):
    """Sensor for nearest incident."""

    def __init__(self, coordinator, entry):
        """Initialize."""
        self.coordinator = coordinator
        self.entry = entry

        self._attr_name = "DGT Incidencia Más Cercana"
        self._attr_unique_id = f"{entry.entry_id}_nearest_incident"
        self._attr_icon = "mdi:map-marker-distance"
        self._attr_native_unit_of_measurement = "km"

    @property
    def state(self):
        """Return distance to nearest incident."""
        incidents = self.coordinator.nearby_incidents or []
        if not incidents:
            return 0

        nearest = min(incidents, key=lambda x: x.get("distance_km", 999))
        return round(nearest.get("distance_km", 0), 1)

    @property
    def extra_state_attributes(self):
        """Return details of nearest incident."""
        incidents = self.coordinator.nearby_incidents or []
        if not incidents:
            return {"description": "Sin incidencias cercanas"}

        nearest = min(incidents, key=lambda x: x.get("distance_km", 999))

        return {
            "description": nearest.get("description", "Desconocido"),
            "type": nearest.get("type", "unknown"),
            "record_type": nearest.get("record_type", ""),
            "severity": nearest.get("severity", "unknown"),
            "road": nearest.get("road"),
            "km_from": nearest.get("km_from"),
            "km_to": nearest.get("km_to"),
            "province": nearest.get("province"),
            "municipality": nearest.get("municipality"),
            "distance_km": round(nearest.get("distance_km", 0), 1),
            "creation_time": nearest.get("creation_time"),
            "cause": nearest.get("detailed_cause", nearest.get("cause_type", "")),
        }


class DGTAllIncidentsSensor(SensorEntity):
    """Sensor with list of all incidents."""

    def __init__(self, coordinator, entry):
        """Initialize."""
        self.coordinator = coordinator
        self.entry = entry

        self._attr_name = "DGT Todas las Incidencias"
        self._attr_unique_id = f"{entry.entry_id}_all_incidents"
        self._attr_icon = "mdi:clipboard-list"

    @property
    def state(self):
        """Return count of all incidents."""
        return len(self.coordinator.nearby_incidents or [])

    @property
    def extra_state_attributes(self):
        """Return list of all incidents (simplified)."""
        incidents = self.coordinator.nearby_incidents or []

        attributes = {
            "total_incidents": len(incidents),
            "last_update": (
                self.coordinator.data.get("last_update")
                if self.coordinator.data
                else None
            ),
        }

        # Add simplified incident list
        if incidents:
            simplified = []
            for inc in incidents[:20]:  # Limit to 20
                simplified.append(
                    {
                        "id": inc.get("id", ""),
                        "description": inc.get("description", ""),
                        "type": inc.get("type", ""),
                        "severity": inc.get("severity", ""),
                        "distance_km": round(inc.get("distance_km", 0), 1),
                        "road": inc.get("road", ""),
                    }
                )
            attributes["incidents"] = simplified

        return attributes


class DGTIncidentsBySeveritySensor(SensorEntity):
    """Sensor for incidents by severity."""

    def __init__(self, coordinator, entry, severity, name):
        """Initialize."""
        self.coordinator = coordinator
        self.entry = entry
        self.severity = severity

        self._attr_name = f"DGT {name}"
        self._attr_unique_id = f"{entry.entry_id}_severity_{severity}"
        self._attr_icon = self._get_icon(severity)
        self._attr_native_unit_of_measurement = "incidencias"

    def _get_icon(self, severity):
        """Get icon for severity."""
        icons = {
            "high": "mdi:alert-octagram",
            "medium": "mdi:alert",
            "low": "mdi:information",
        }
        return icons.get(severity, "mdi:alert")

    @property
    def state(self):
        """Return incidents count for this severity."""
        incidents = self.coordinator.incidents_by_severity.get(self.severity, [])
        return len(incidents)

    @property
    def extra_state_attributes(self):
        """Return incidents for this severity."""
        incidents = self.coordinator.incidents_by_severity.get(self.severity, [])

        attributes = {
            "incidents_count": len(incidents),
            "last_update": (
                self.coordinator.data.get("last_update")
                if self.coordinator.data
                else None
            ),
        }

        # Add incident details
        if incidents:
            details = []
            for inc in incidents[:5]:
                details.append(
                    {
                        "description": inc.get("description", ""),
                        "type": inc.get("type", ""),
                        "distance_km": round(inc.get("distance_km", 0), 1),
                        "road": inc.get("road", ""),
                        "creation_time": inc.get("creation_time"),
                    }
                )
            attributes["incidents"] = details

        return attributes
