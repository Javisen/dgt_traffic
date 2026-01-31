"""Data coordinator for DGT Traffic."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List
from collections import defaultdict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util
from geopy.distance import geodesic

from .const import (
    DOMAIN,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_MAX_AGE_DAYS,
    DEFAULT_RADIUS_KM,
    CONF_RADIUS_KM,
    CONF_MAX_AGE_DAYS,
    CONF_UPDATE_INTERVAL,
)

from .api.dgt_client import DGTClient

_LOGGER = logging.getLogger(__name__)


class DGTCoordinator(DataUpdateCoordinator):
    """Coordinator for DGT Traffic."""

    def __init__(self, hass: HomeAssistant, client: DGTClient, config: Dict[str, Any]):
        """Initialize."""
        self.hass = hass
        self.client = client
        self.config = config

        # User location - USAR LAS DE HA
        self.user_lat = hass.config.latitude
        self.user_lon = hass.config.longitude

        # Configuración
        self.radius_km = config.get(CONF_RADIUS_KM, DEFAULT_RADIUS_KM)
        self.max_age_days = config.get(CONF_MAX_AGE_DAYS, DEFAULT_MAX_AGE_DAYS)

        # Data storage
        self.all_incidents = []
        self.nearby_incidents = []
        self.incidents_by_type = defaultdict(list)
        self.incidents_by_severity = defaultdict(list)

        # Calculate update interval
        update_interval = timedelta(
            minutes=config.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from DGT API and process it."""
        _LOGGER.debug("Updating DGT traffic data")

        try:
            # Get all incidents
            all_incidents = await self.client.get_incidents(self.max_age_days)
            self.all_incidents = all_incidents

            # Filter by distance and process
            self.nearby_incidents = []
            self.incidents_by_type = defaultdict(list)
            self.incidents_by_severity = defaultdict(list)

            for incident in all_incidents:
                # Calculate distance
                distance = self._calculate_distance(incident)
                incident["distance_km"] = distance

                # Check if within radius
                if distance <= self.radius_km:
                    self.nearby_incidents.append(incident)

                    # Group by type
                    inc_type = incident.get("type", "other")
                    self.incidents_by_type[inc_type].append(incident)

                    # Group by severity
                    severity = incident.get("severity", "unknown")
                    self.incidents_by_severity[severity].append(incident)

            # Sort nearby incidents by distance
            self.nearby_incidents.sort(key=lambda x: x.get("distance_km", 999))

            # Prepare statistics
            stats = self._prepare_statistics()

            _LOGGER.info(
                "Updated DGT data: %s total, %s nearby, %s types",
                len(all_incidents),
                len(self.nearby_incidents),
                len(self.incidents_by_type),
            )

            return {
                "all_incidents": all_incidents,
                "nearby_incidents": self.nearby_incidents,
                "incidents_by_type": dict(self.incidents_by_type),
                "incidents_by_severity": dict(self.incidents_by_severity),
                "statistics": stats,
                "last_update": dt_util.utcnow().isoformat(),
                "user_location": {
                    "latitude": self.user_lat,
                    "longitude": self.user_lon,
                    "radius_km": self.radius_km,
                },
            }

        except Exception as err:
            _LOGGER.error("Error updating DGT data: %s", err)
            # Return cached data if available
            if hasattr(self, "data") and self.data:
                return self.data
            raise

    def _calculate_distance(self, incident: Dict) -> float:
        """Calculate distance from user to incident in km."""
        try:
            inc_lat = incident.get("latitude")
            inc_lon = incident.get("longitude")

            if not inc_lat or not inc_lon:
                return 999.0  # Far away if no coordinates

            user_coords = (self.user_lat, self.user_lon)
            inc_coords = (float(inc_lat), float(inc_lon))

            return geodesic(user_coords, inc_coords).kilometers

        except Exception:
            return 999.0

    def _prepare_statistics(self) -> Dict[str, Any]:
        """Prepare statistics about incidents."""
        stats = {
            "total": len(self.all_incidents),
            "nearby": len(self.nearby_incidents),
            "by_type": {},
            "by_severity": {},
            "closest": None,
            "most_severe": None,
        }

        # Count by type
        for inc_type, incidents in self.incidents_by_type.items():
            stats["by_type"][inc_type] = len(incidents)

        # Count by severity
        for severity, incidents in self.incidents_by_severity.items():
            stats["by_severity"][severity] = len(incidents)

        # Find closest incident
        if self.nearby_incidents:
            closest = min(
                self.nearby_incidents, key=lambda x: x.get("distance_km", 999)
            )
            stats["closest"] = {
                "description": closest.get("description", ""),
                "distance_km": closest.get("distance_km", 0),
                "type": closest.get("type", ""),
                "severity": closest.get("severity", ""),
            }

        # Find most severe nearby incident
        severity_order = {"highest": 4, "high": 3, "medium": 2, "low": 1, "unknown": 0}
        if self.nearby_incidents:
            most_severe = max(
                self.nearby_incidents,
                key=lambda x: severity_order.get(x.get("severity", "unknown"), 0),
            )
            stats["most_severe"] = {
                "description": most_severe.get("description", ""),
                "severity": most_severe.get("severity", ""),
                "type": most_severe.get("type", ""),
            }

        return stats
