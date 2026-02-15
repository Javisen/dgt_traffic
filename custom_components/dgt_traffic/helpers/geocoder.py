"""Geocoder helper for DGT Traffic."""

import logging
import aiohttp
from typing import Optional, Tuple
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class DGTGeocoder:
    """Geocoder for converting municipality names to coordinates."""

    @staticmethod
    async def async_get_coordinates(
        hass: HomeAssistant, municipality: str, province: str = ""
    ) -> Optional[Tuple[float, float]]:
        """Get coordinates from municipality and province."""
        try:
            # Primero intentar con Nominatim (OpenStreetMap)
            coordinates = await DGTGeocoder._async_get_from_nominatim(
                hass, municipality, province
            )

            if coordinates:
                return coordinates

            # Fallback a Google Maps API (sin clave)
            coordinates = await DGTGeocoder._async_get_from_google(
                hass, municipality, province
            )

            return coordinates

        except Exception as err:
            _LOGGER.error("Error geocoding %s, %s: %s", municipality, province, err)
            return None

    @staticmethod
    async def _async_get_from_nominatim(
        hass: HomeAssistant, municipality: str, province: str = ""
    ) -> Optional[Tuple[float, float]]:
        """Get coordinates from OpenStreetMap Nominatim."""
        try:
            # Construir query
            query = (
                f"{municipality}, {province}, Spain"
                if province
                else f"{municipality}, Spain"
            )
            query = query.replace(" ", "%20")

            url = f"https://nominatim.openstreetmap.org/search?q={query}&format=json&limit=1"

            headers = {
                "User-Agent": "HomeAssistant-DGT-Traffic/1.0",
                "Accept": "application/json",
            }

            session = hass.helpers.aiohttp_client.async_get_clientsession()

            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and len(data) > 0:
                        lat = float(data[0]["lat"])
                        lon = float(data[0]["lon"])
                        return (lat, lon)

            return None

        except Exception:
            return None

    @staticmethod
    async def _async_get_from_google(
        hass: HomeAssistant, municipality: str, province: str = ""
    ) -> Optional[Tuple[float, float]]:
        """Get coordinates from Google Maps (fallback)."""
        try:
            query = (
                f"{municipality}, {province}, Spain"
                if province
                else f"{municipality}, Spain"
            )
            query = query.replace(" ", "+")

            url = f"https://maps.googleapis.com/maps/api/geocode/json?address={query}&region=es"

            session = hass.helpers.aiohttp_client.async_get_clientsession()

            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "OK" and data.get("results"):
                        location = data["results"][0]["geometry"]["location"]
                        return (location["lat"], location["lng"])

            return None

        except Exception:
            return None

    @staticmethod
    async def async_get_city_from_coordinates(
        hass: HomeAssistant, latitude: float, longitude: float
    ) -> Optional[Tuple[str, str]]:
        """Get municipality and province from coordinates (reverse geocoding)."""
        try:
            url = f"https://nominatim.openstreetmap.org/reverse?lat={latitude}&lon={longitude}&format=json"

            headers = {
                "User-Agent": "HomeAssistant-DGT-Traffic/1.0",
                "Accept": "application/json",
            }

            session = hass.helpers.aiohttp_client.async_get_clientsession()

            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    address = data.get("address", {})

                    municipality = (
                        address.get("city")
                        or address.get("town")
                        or address.get("village")
                    )
                    province = address.get("state") or address.get("county", "")

                    # Limpiar provincia
                    if province and "Comunidad" in province:
                        province = province.replace("Comunidad ", "").replace(
                            "Comunitat ", ""
                        )

                    if municipality:
                        return (municipality, province)

            return None

        except Exception as err:
            _LOGGER.error("Reverse geocoding failed: %s", err)
            return None
