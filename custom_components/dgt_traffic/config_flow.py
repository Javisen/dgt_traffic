"""Config flow for DGT Traffic."""

from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
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
    CONF_CUSTOM_LATITUDE,
    CONF_CUSTOM_LONGITUDE,
    CONF_LOCATION_NAME,
    CONF_LOCATION_MODE,
    CONF_PERSON_ENTITY,
    LOCATION_MODE_HA,
    LOCATION_MODE_CUSTOM,
    LOCATION_MODE_PERSON,
    DEFAULT_RADIUS_KM,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_MAX_AGE_DAYS,
    DEFAULT_CHARGING_RADIUS_KM,
    DEFAULT_SHOW_ONLY_AVAILABLE,
)

_LOGGER = logging.getLogger(__name__)


def _build_location_name(data):
    name = ""
    if data.get(CONF_MUNICIPALITY):
        name = data[CONF_MUNICIPALITY]
    if data.get(CONF_PROVINCE):
        if name:
            name = f"{name}, {data[CONF_PROVINCE]}"
        else:
            name = data[CONF_PROVINCE]
    return name


class DGTConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            if user_input["selected_module"] == "incidents":
                return await self.async_step_incidents()
            return await self.async_step_charging()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("selected_module", default="incidents"): vol.In(
                        {
                            "incidents": "DGT Incidencias",
                            "charging": "DGT Electrolineras",
                        }
                    )
                }
            ),
        )

    # ================= INCIDENCIAS =================

    async def async_step_incidents(self, user_input=None):
        errors = {}

        if user_input is not None:
            mode = user_input.get(CONF_LOCATION_MODE)
            desired_name = _build_location_name(user_input)

            # PERSONA (NO TOCAR NOMBRE)
            if mode == LOCATION_MODE_PERSON:
                person = user_input.get(CONF_PERSON_ENTITY)
                state = self.hass.states.get(person)

                if not state:
                    errors["base"] = "person_not_found"
                elif state.attributes.get("latitude") is None:
                    errors["base"] = "person_no_gps"
                else:
                    user_input[CONF_CUSTOM_LATITUDE] = round(
                        float(state.attributes["latitude"]), 6
                    )
                    user_input[CONF_CUSTOM_LONGITUDE] = round(
                        float(state.attributes["longitude"]), 6
                    )
                    user_input[CONF_LOCATION_NAME] = state.name

            # CUSTOM / HA / GEOCODER → SIEMPRE MUNICIPIO
            else:
                try:
                    if mode == LOCATION_MODE_CUSTOM:
                        user_input[CONF_CUSTOM_LATITUDE] = round(
                            float(user_input.get(CONF_CUSTOM_LATITUDE)), 6
                        )
                        user_input[CONF_CUSTOM_LONGITUDE] = round(
                            float(user_input.get(CONF_CUSTOM_LONGITUDE)), 6
                        )

                    else:
                        coords = await DGTGeocoder.async_get_coordinates(
                            self.hass,
                            municipality=user_input.get(CONF_MUNICIPALITY, ""),
                            province=user_input.get(CONF_PROVINCE, ""),
                        )

                        if coords:
                            user_input[CONF_CUSTOM_LATITUDE] = round(coords[0], 6)
                            user_input[CONF_CUSTOM_LONGITUDE] = round(coords[1], 6)
                        else:
                            raise Exception("Geocoder failed")

                    user_input[CONF_LOCATION_NAME] = desired_name or "Ubicación HA"

                except Exception:
                    try:
                        user_input[CONF_CUSTOM_LATITUDE] = round(
                            self.hass.config.latitude, 6
                        )
                        user_input[CONF_CUSTOM_LONGITUDE] = round(
                            self.hass.config.longitude, 6
                        )
                        user_input[CONF_LOCATION_NAME] = desired_name or "Ubicación HA"
                    except Exception:
                        errors["base"] = "invalid_coordinates"

            if not errors:
                user_input[CONF_ENABLE_INCIDENTS] = True
                user_input[CONF_ENABLE_CHARGING] = False

                return self.async_create_entry(
                    title=f"DGT Incidencias - {user_input[CONF_LOCATION_NAME]}",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="incidents",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LOCATION_MODE, default=LOCATION_MODE_HA): vol.In(
                        {
                            LOCATION_MODE_HA: "Ubicación Home Assistant",
                            LOCATION_MODE_CUSTOM: "Coordenadas personalizadas",
                            LOCATION_MODE_PERSON: "Seguir persona",
                        }
                    ),
                    vol.Optional(CONF_PERSON_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="person")
                    ),
                    vol.Optional(CONF_MUNICIPALITY, default=""): str,
                    vol.Optional(CONF_PROVINCE, default=""): str,
                    vol.Optional(CONF_CUSTOM_LATITUDE): vol.Coerce(float),
                    vol.Optional(CONF_CUSTOM_LONGITUDE): vol.Coerce(float),
                    vol.Optional(CONF_RADIUS_KM, default=DEFAULT_RADIUS_KM): vol.Coerce(
                        int
                    ),
                    vol.Optional(
                        CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
                    ): vol.Coerce(int),
                    vol.Optional(
                        CONF_MAX_AGE_DAYS, default=DEFAULT_MAX_AGE_DAYS
                    ): vol.Coerce(int),
                }
            ),
            errors=errors,
        )

    # ================= CHARGING =================

    async def async_step_charging(self, user_input=None):
        errors = {}

        if user_input is not None:
            mode = user_input.get(CONF_LOCATION_MODE)
            desired_name = _build_location_name(user_input)

            if mode == LOCATION_MODE_PERSON:
                person = user_input.get(CONF_PERSON_ENTITY)
                state = self.hass.states.get(person)

                if not state:
                    errors["base"] = "person_not_found"
                elif state.attributes.get("latitude") is None:
                    errors["base"] = "person_no_gps"
                else:
                    user_input[CONF_CUSTOM_LATITUDE] = round(
                        float(state.attributes["latitude"]), 6
                    )
                    user_input[CONF_CUSTOM_LONGITUDE] = round(
                        float(state.attributes["longitude"]), 6
                    )
                    user_input[CONF_LOCATION_NAME] = state.name

            else:
                try:
                    if mode == LOCATION_MODE_CUSTOM:
                        user_input[CONF_CUSTOM_LATITUDE] = round(
                            float(user_input.get(CONF_CUSTOM_LATITUDE)), 6
                        )
                        user_input[CONF_CUSTOM_LONGITUDE] = round(
                            float(user_input.get(CONF_CUSTOM_LONGITUDE)), 6
                        )
                    else:
                        coords = await DGTGeocoder.async_get_coordinates(
                            self.hass,
                            municipality=user_input.get(CONF_MUNICIPALITY, ""),
                            province=user_input.get(CONF_PROVINCE, ""),
                        )

                        if coords:
                            user_input[CONF_CUSTOM_LATITUDE] = round(coords[0], 6)
                            user_input[CONF_CUSTOM_LONGITUDE] = round(coords[1], 6)
                        else:
                            raise Exception()

                    user_input[CONF_LOCATION_NAME] = desired_name or "Ubicación HA"

                except Exception:
                    user_input[CONF_CUSTOM_LATITUDE] = round(
                        self.hass.config.latitude, 6
                    )
                    user_input[CONF_CUSTOM_LONGITUDE] = round(
                        self.hass.config.longitude, 6
                    )
                    user_input[CONF_LOCATION_NAME] = desired_name or "Ubicación HA"

            if not errors:
                user_input[CONF_ENABLE_INCIDENTS] = False
                user_input[CONF_ENABLE_CHARGING] = True

                return self.async_create_entry(
                    title=f"DGT Electrolineras - {user_input[CONF_LOCATION_NAME]}",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="charging",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LOCATION_MODE, default=LOCATION_MODE_HA): vol.In(
                        {
                            LOCATION_MODE_HA: "Ubicación Home Assistant",
                            LOCATION_MODE_CUSTOM: "Coordenadas personalizadas",
                            LOCATION_MODE_PERSON: "Seguir persona",
                        }
                    ),
                    vol.Optional(CONF_PERSON_ENTITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="person")
                    ),
                    vol.Optional(CONF_MUNICIPALITY, default=""): str,
                    vol.Optional(CONF_PROVINCE, default=""): str,
                    vol.Optional(CONF_CUSTOM_LATITUDE): vol.Coerce(float),
                    vol.Optional(CONF_CUSTOM_LONGITUDE): vol.Coerce(float),
                    vol.Optional(
                        CONF_CHARGING_RADIUS_KM, default=DEFAULT_CHARGING_RADIUS_KM
                    ): vol.Coerce(int),
                    vol.Optional(
                        CONF_SHOW_ONLY_AVAILABLE, default=DEFAULT_SHOW_ONLY_AVAILABLE
                    ): bool,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return DGTOptionsFlow(config_entry)
