"""Config flow for DGT Traffic."""

from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
import logging

from .options_flow import DGTOptionsFlow
from .helpers.geocoder import DGTGeocoder
from .const import (
    DOMAIN,
    CONF_MUNICIPALITY,
    CONF_PROVINCE,
    CONF_RADIUS_KM,
    CONF_UPDATE_INTERVAL,
    CONF_MAX_AGE_DAYS,
    CONF_ENABLE_INCIDENTS,
    CONF_ENABLE_CHARGING,
    CONF_CHARGING_RADIUS_KM,
    CONF_SHOW_ONLY_AVAILABLE,
    CONF_USE_CUSTOM_LOCATION,
    CONF_CUSTOM_LATITUDE,
    CONF_CUSTOM_LONGITUDE,
    CONF_LOCATION_NAME,
    DEFAULT_RADIUS_KM,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_MAX_AGE_DAYS,
    DEFAULT_CHARGING_RADIUS_KM,
    DEFAULT_SHOW_ONLY_AVAILABLE,
)

_LOGGER = logging.getLogger(__name__)


class DGTConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow profesional para DGT Traffic."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Primer menú: elegir módulo."""
        if user_input is not None:
            self.selected_module = user_input["selected_module"]

            if self.selected_module == "incidents":
                return await self.async_step_incidents()

            if self.selected_module == "charging":
                return await self.async_step_charging()

        schema = vol.Schema(
            {
                vol.Required("selected_module", default="incidents"): vol.In(
                    {
                        "incidents": "DGT Incidencias",
                        "charging": "DGT Electrolineras",
                    }
                )
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            description_placeholders={"intro": "Bienvenido a DGT Traffic"},
        )

    # ---------MÓDULO DE INCIDENCIAS---------------

    async def async_step_incidents(self, user_input=None):
        """Configuración del módulo de incidencias."""
        errors = {}

        if user_input is not None:
            use_custom = user_input.get(CONF_USE_CUSTOM_LOCATION, False)

            if use_custom:
                try:
                    lat_raw = str(user_input.get(CONF_CUSTOM_LATITUDE, "0")).replace(
                        ",", "."
                    )

                    user_input[CONF_CUSTOM_LATITUDE] = round(float(lat_raw), 6)

                    lon_raw = str(user_input.get(CONF_CUSTOM_LONGITUDE, "0")).replace(
                        ",", "."
                    )
                    user_input[CONF_CUSTOM_LONGITUDE] = round(float(lon_raw), 6)

                    user_input[CONF_LOCATION_NAME] = user_input.get(
                        CONF_MUNICIPALITY, "Ubicación personalizada"
                    )
                except (ValueError, TypeError) as err:
                    _LOGGER.error(
                        "Error al procesar coordenadas en incidencias: %s", err
                    )
                    errors["base"] = "invalid_coordinates"
            else:
                location_str = ""
                if user_input.get(CONF_MUNICIPALITY):
                    location_str = user_input[CONF_MUNICIPALITY]
                if user_input.get(CONF_PROVINCE):
                    location_str = f"{location_str}, {user_input[CONF_PROVINCE]}"

                if not location_str.strip():
                    location_str = "España"

                try:
                    coordinates = await DGTGeocoder.async_get_coordinates(
                        self.hass,
                        municipality=user_input.get(CONF_MUNICIPALITY, ""),
                        province=user_input.get(CONF_PROVINCE, ""),
                    )

                    if coordinates:
                        user_input[CONF_CUSTOM_LATITUDE] = round(
                            float(coordinates[0]), 6
                        )
                        user_input[CONF_CUSTOM_LONGITUDE] = round(
                            float(coordinates[1]), 6
                        )
                        user_input[CONF_LOCATION_NAME] = location_str
                    else:
                        user_input[CONF_CUSTOM_LATITUDE] = round(
                            float(self.hass.config.latitude), 6
                        )
                        user_input[CONF_CUSTOM_LONGITUDE] = round(
                            float(self.hass.config.longitude), 6
                        )
                        user_input[CONF_LOCATION_NAME] = user_input.get(
                            CONF_MUNICIPALITY, "Ubicación HA"
                        )
                except Exception:
                    user_input[CONF_CUSTOM_LATITUDE] = round(
                        float(self.hass.config.latitude), 6
                    )
                    user_input[CONF_CUSTOM_LONGITUDE] = round(
                        float(self.hass.config.longitude), 6
                    )

            if not errors:
                user_input[CONF_ENABLE_INCIDENTS] = True
                user_input[CONF_ENABLE_CHARGING] = False

                return self.async_create_entry(
                    title=f"DGT Incidencias - {user_input[CONF_LOCATION_NAME]}",
                    data=user_input,
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_USE_CUSTOM_LOCATION, default=False): bool,
                vol.Optional(CONF_MUNICIPALITY, default=""): str,
                vol.Optional(CONF_PROVINCE, default=""): str,
                vol.Optional(CONF_CUSTOM_LATITUDE): vol.Coerce(float),
                vol.Optional(CONF_CUSTOM_LONGITUDE): vol.Coerce(float),
                vol.Optional(CONF_RADIUS_KM, default=DEFAULT_RADIUS_KM): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=500)
                ),
                vol.Optional(
                    CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=1440)),
                vol.Optional(CONF_MAX_AGE_DAYS, default=DEFAULT_MAX_AGE_DAYS): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=30)
                ),
            }
        )

        return self.async_show_form(
            step_id="incidents",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "note": "Nota: Las coordenadas se redondearán automáticamente a 6 decimales."
            },
        )

    # --------MÓDULO DE ELECTROLINERAS-----------------

    async def async_step_charging(self, user_input=None):
        """Configuración del módulo de electrolineras."""
        errors = {}

        if user_input is not None:
            # Determinar si usa ubicación personalizada o geopy
            use_custom = user_input.get(CONF_USE_CUSTOM_LOCATION, False)

            if use_custom:
                # USAR COORDENADAS PERSONALIZADAS CON LIMPIEZA
                try:
                    lat_raw = str(user_input.get(CONF_CUSTOM_LATITUDE, "0")).replace(
                        ",", "."
                    )
                    user_input[CONF_CUSTOM_LATITUDE] = round(float(lat_raw), 6)

                    lon_raw = str(user_input.get(CONF_CUSTOM_LONGITUDE, "0")).replace(
                        ",", "."
                    )
                    user_input[CONF_CUSTOM_LONGITUDE] = round(float(lon_raw), 6)

                    user_input[CONF_LOCATION_NAME] = user_input.get(
                        CONF_MUNICIPALITY, "Ubicación personalizada"
                    )
                except (ValueError, TypeError) as err:
                    _LOGGER.error("Error al procesar coordenadas en charging: %s", err)
                    errors["base"] = "invalid_coordinates"
            else:
                # USAR GEOCODER con municipio/provincia
                location_str = ""
                if user_input.get(CONF_MUNICIPALITY):
                    location_str = user_input[CONF_MUNICIPALITY]
                if user_input.get(CONF_PROVINCE):
                    location_str = f"{location_str}, {user_input[CONF_PROVINCE]}"

                if not location_str.strip():
                    location_str = "España"

                try:
                    coordinates = await DGTGeocoder.async_get_coordinates(
                        self.hass,
                        municipality=user_input.get(CONF_MUNICIPALITY, ""),
                        province=user_input.get(CONF_PROVINCE, ""),
                    )

                    if coordinates:
                        user_input[CONF_CUSTOM_LATITUDE] = round(
                            float(coordinates[0]), 6
                        )
                        user_input[CONF_CUSTOM_LONGITUDE] = round(
                            float(coordinates[1]), 6
                        )
                        user_input[CONF_LOCATION_NAME] = location_str
                    else:
                        # Fallback a coordenadas de HA redondeadas
                        user_input[CONF_CUSTOM_LATITUDE] = round(
                            float(self.hass.config.latitude), 6
                        )
                        user_input[CONF_CUSTOM_LONGITUDE] = round(
                            float(self.hass.config.longitude), 6
                        )
                        user_input[CONF_LOCATION_NAME] = user_input.get(
                            CONF_MUNICIPALITY, "Ubicación HA"
                        )
                except Exception:
                    user_input[CONF_CUSTOM_LATITUDE] = round(
                        float(self.hass.config.latitude), 6
                    )
                    user_input[CONF_CUSTOM_LONGITUDE] = round(
                        float(self.hass.config.longitude), 6
                    )

            if not errors:
                user_input[CONF_ENABLE_INCIDENTS] = False
                user_input[CONF_ENABLE_CHARGING] = True

                return self.async_create_entry(
                    title=f"DGT Electrolineras - {user_input[CONF_LOCATION_NAME]}",
                    data=user_input,
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_USE_CUSTOM_LOCATION, default=False): bool,
                vol.Optional(CONF_MUNICIPALITY, default=""): str,
                vol.Optional(CONF_PROVINCE, default=""): str,
                vol.Optional(CONF_CUSTOM_LATITUDE): vol.Coerce(float),
                vol.Optional(CONF_CUSTOM_LONGITUDE): vol.Coerce(float),
                vol.Optional(
                    CONF_CHARGING_RADIUS_KM, default=DEFAULT_CHARGING_RADIUS_KM
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=500)),
                vol.Optional(
                    CONF_SHOW_ONLY_AVAILABLE, default=DEFAULT_SHOW_ONLY_AVAILABLE
                ): bool,
            }
        )

        return self.async_show_form(
            step_id="charging",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "note": "Nota: Las coordenadas se redondearán automáticamente a 6 decimales para optimizar el filtrado."
            },
        )

    # -------OPTIONS FLOW--------

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return DGTOptionsFlow(config_entry)
