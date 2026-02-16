"""
DGT Traffic - Versión modular.
"""

import logging
from typing import Dict, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_ENABLE_INCIDENTS, CONF_ENABLE_CHARGING

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up DGT Traffic - Versión modular."""
    _LOGGER.info("Setting up DGT Traffic (Modular)")

    config = {**entry.data}
    if entry.options:
        config.update(entry.options)
        _LOGGER.info("Usando configuración combinada (data + options)")

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"modules": {}}

    try:
        modules_config = {}
        platforms_to_load = []

        if config.get(CONF_ENABLE_INCIDENTS, True):
            try:
                from .modules.incidents import DGTIncidentsModule

                incidents_module = DGTIncidentsModule(hass, config)
                if await incidents_module.async_setup():
                    hass.data[DOMAIN][entry.entry_id]["modules"][
                        "incidents"
                    ] = incidents_module
                    modules_config["incidents"] = True
                    platforms_to_load.extend([Platform.SENSOR, Platform.BINARY_SENSOR])
                    _LOGGER.info("Módulo de incidencias configurado correctamente")
                else:
                    _LOGGER.error("Error al configurar módulo de incidencias")
                    modules_config["incidents"] = False
            except Exception as err:
                _LOGGER.error("Error inicializando módulo de incidencias: %s", err)
                modules_config["incidents"] = False

        if config.get(CONF_ENABLE_CHARGING, False):
            try:
                from .modules.charging import DGTChargingModule

                charging_module = DGTChargingModule(hass, config)
                if await charging_module.async_setup():
                    hass.data[DOMAIN][entry.entry_id]["modules"][
                        "charging"
                    ] = charging_module
                    modules_config["charging"] = True
                    platforms_to_load.extend([Platform.SENSOR, Platform.BINARY_SENSOR])
                    _LOGGER.info("Módulo de electrolineras configurado correctamente")
                else:
                    _LOGGER.error("Error al configurar módulo de electrolineras")
                    modules_config["charging"] = False
            except Exception as err:
                _LOGGER.error("Error inicializando módulo de electrolineras: %s", err)
                modules_config["charging"] = False

        if platforms_to_load:
            platforms_to_load = list(set(platforms_to_load))
            await hass.config_entries.async_forward_entry_setups(
                entry, platforms_to_load
            )
            _LOGGER.info("Plataformas cargadas: %s", platforms_to_load)
        else:
            _LOGGER.warning("No se cargaron plataformas (ningún módulo habilitado)")

        hass.data[DOMAIN][entry.entry_id]["modules_config"] = modules_config

        await _async_setup_services(hass, entry)

        async def async_update_options(hass: HomeAssistant, entry: ConfigEntry):
            """Handle options update."""
            _LOGGER.info("Opciones cambiadas, recargando entrada completa...")
            await hass.config_entries.async_reload(entry.entry_id)
            return True

        entry.async_on_unload(entry.add_update_listener(async_update_options))

        return True

    except ImportError as e:
        _LOGGER.error("Error importando estructura modular: %s", e)
        _LOGGER.info("Intentando usar estructura vieja...")

        try:
            from .coordinator import DGTCoordinator
            from .api.dgt_client import DGTClient

            _LOGGER.warning("Usando estructura vieja (modo compatibilidad)")

            await hass.config_entries.async_forward_entry_setups(
                entry, [Platform.SENSOR, Platform.BINARY_SENSOR]
            )

            return True

        except ImportError as e2:
            _LOGGER.error("Error en estructura vieja: %s", e2)
            return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading DGT Traffic")

    # Eliminar servicios
    for service in [
        "refresh",
        "refresh_charging",
        "get_incidents",
        "test_connection",
        "diagnose",
    ]:
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)

    entry_data = hass.data[DOMAIN].get(entry.entry_id, {})
    modules = entry_data.get("modules", {})

    for module_name, module in modules.items():
        if hasattr(module, "async_unload"):
            await module.async_unload()
        _LOGGER.info("Módulo %s descargado", module_name)

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, [Platform.SENSOR, Platform.BINARY_SENSOR]
    )

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        _LOGGER.info("DGT Traffic descargado correctamente")
    else:
        _LOGGER.warning("No se pudieron descargar todas las plataformas")

    return unload_ok


async def _async_setup_services(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Configurar servicios de integración."""

    async def handle_refresh_charging(call):
        """Handle refresh charging service."""
        _LOGGER.info("Servicio refresh charging llamado")
        entry_data = hass.data[DOMAIN].get(entry.entry_id, {})

        charging_module = entry_data.get("modules", {}).get("charging")
        if charging_module and charging_module.coordinator:
            await charging_module.coordinator.async_refresh()
            _LOGGER.info("Datos electrolineras actualizados manualmente")
        else:
            _LOGGER.warning("No se pudo refrescar electrolineras: módulo no encontrado")

    async def handle_refresh_incidents(call):
        """Handle refresh incidents service."""
        _LOGGER.info("Servicio refresh incidents llamado")
        entry_data = hass.data[DOMAIN].get(entry.entry_id, {})

        incidents_module = entry_data.get("modules", {}).get("incidents")
        if incidents_module and incidents_module.coordinator:
            await incidents_module.coordinator.async_refresh()
            _LOGGER.info("Datos incidencias actualizados manualmente")
        else:
            _LOGGER.warning("No se pudo refrescar incidencias: módulo no encontrado")

    async def handle_diagnose(call):
        """Diagnose DGT Traffic integration."""
        _LOGGER.info("=== DGT TRAFFIC DIAGNOSIS ===")

        if DOMAIN not in hass.data:
            _LOGGER.error("DGT Traffic not in hass.data")
            return

        for entry_id, entry_data in hass.data[DOMAIN].items():
            _LOGGER.info("Entry ID: %s", entry_id)
            _LOGGER.info(
                "Modules loaded: %s", list(entry_data.get("modules", {}).keys())
            )
            _LOGGER.info("Modules config: %s", entry_data.get("modules_config", {}))

            config_entry = hass.config_entries.async_get_entry(entry_id)
            if config_entry:
                mode = config_entry.data.get("location_mode", "ha")
                _LOGGER.info("Location mode: %s", mode)
                if mode == "person":
                    person = config_entry.data.get("person_entity")
                    _LOGGER.info("Following person: %s", person)
                    if person:
                        state = hass.states.get(person)
                        if state:
                            _LOGGER.info("Person state: %s", state.state)
                            _LOGGER.info("Person attributes: %s", state.attributes)

            modules = entry_data.get("modules", {})
            for module_name, module in modules.items():
                _LOGGER.info("MODULE: %s", module_name.upper())
                _LOGGER.info("   Enabled: %s", module.enabled)
                _LOGGER.info("   Coordinates: %s, %s", module.user_lat, module.user_lon)

                if hasattr(module, "coordinator") and module.coordinator:
                    _LOGGER.info(
                        "   Last update success: %s",
                        module.coordinator.last_update_success,
                    )
                    if module.coordinator.data:
                        if module_name == "charging":
                            nearby = len(
                                module.coordinator.data.get("nearby_stations", [])
                            )
                            _LOGGER.info("   Nearby stations: %s", nearby)
                        else:
                            nearby = len(
                                module.coordinator.data.get("nearby_incidents", [])
                            )
                            _LOGGER.info("   Nearby incidents: %s", nearby)

        _LOGGER.info("=== END DIAGNOSIS ===")

    # Registrar servicios
    if not hass.services.has_service(DOMAIN, "refresh_charging"):
        hass.services.async_register(
            DOMAIN, "refresh_charging", handle_refresh_charging
        )

    if not hass.services.has_service(DOMAIN, "refresh_incidents"):
        hass.services.async_register(
            DOMAIN, "refresh_incidents", handle_refresh_incidents
        )

    if not hass.services.has_service(DOMAIN, "diagnose"):
        hass.services.async_register(DOMAIN, "diagnose", handle_diagnose)

    _LOGGER.info("Servicios DGT Traffic registrados")
