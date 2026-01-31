"""Binary sensors for DGT Traffic."""

import logging
from homeassistant.components.binary_sensor import BinarySensorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up DGT binary sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    sensors = [
        DGTBinarySensor(coordinator, entry, "any", "DGT Hay Incidencias"),
        DGTBinarySensor(coordinator, entry, "weather", "DGT Alertas Meteorológicas"),
        DGTBinarySensor(coordinator, entry, "roadworks", "DGT Hay Obras"),
        DGTBinarySensor(coordinator, entry, "accident", "DGT Hay Accidentes"),
        DGTBinarySensor(coordinator, entry, "obstruction", "DGT Hay Obstáculos"),
    ]

    async_add_entities(sensors, True)


class DGTBinarySensor(BinarySensorEntity):
    """Binary sensor for DGT incidents."""

    def __init__(self, coordinator, entry, sensor_type, name):
        """Initialize."""
        self.coordinator = coordinator
        self.entry = entry
        self.sensor_type = sensor_type

        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_binary_{sensor_type}"
        self._attr_device_class = "problem"
        self._attr_icon = self._get_icon(sensor_type)

    def _get_icon(self, sensor_type):
        """Get icon for binary sensor."""
        icons = {
            "any": "mdi:car-alert",
            "weather": "mdi:weather-alert",
            "roadworks": "mdi:road-variant",
            "accident": "mdi:car-brake-alert",
            "obstruction": "mdi:alert-octagon",
        }
        return icons.get(sensor_type, "mdi:alert")

    @property
    def is_on(self):
        """Return True if there are incidents of this type."""
        if self.sensor_type == "any":
            # Check if any incidents nearby
            return len(self.coordinator.nearby_incidents or []) > 0
        else:
            # Check specific type
            incidents = self.coordinator.incidents_by_type.get(self.sensor_type, [])
            return len(incidents) > 0

    @property
    def extra_state_attributes(self):
        """Return additional attributes."""
        if self.sensor_type == "any":
            incidents = self.coordinator.nearby_incidents or []
        else:
            incidents = self.coordinator.incidents_by_type.get(self.sensor_type, [])

        attributes = {
            "incidents_count": len(incidents),
            "last_update": (
                self.coordinator.data.get("last_update")
                if self.coordinator.data
                else None
            ),
        }

        # Add most severe incident if any
        if incidents:
            # Find most severe
            severity_order = {
                "highest": 4,
                "high": 3,
                "medium": 2,
                "low": 1,
                "unknown": 0,
            }
            most_severe = max(
                incidents,
                key=lambda x: severity_order.get(x.get("severity", "unknown"), 0),
            )

            attributes.update(
                {
                    "most_severe_description": most_severe.get("description", ""),
                    "most_severe_severity": most_severe.get("severity", ""),
                    "most_severe_distance_km": round(
                        most_severe.get("distance_km", 0), 1
                    ),
                }
            )

        return attributes
