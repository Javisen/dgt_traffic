"""Constants for DGT Traffic."""

from datetime import timedelta
from homeassistant.const import Platform

DOMAIN = "dgt_traffic"
PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]

# --------------------
# Location system
# --------------------

CONF_LOCATION_MODE = "location_mode"
CONF_PERSON_ENTITY = "person_entity"

LOCATION_MODE_HA = "ha"
LOCATION_MODE_CUSTOM = "custom"
LOCATION_MODE_PERSON = "person"

CONF_CUSTOM_LATITUDE = "custom_latitude"
CONF_CUSTOM_LONGITUDE = "custom_longitude"
CONF_LOCATION_NAME = "location_name"

# --------------------
# Generic config
# --------------------

CONF_RADIUS_KM = "radius_km"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_MAX_AGE_DAYS = "max_age_days"
CONF_MUNICIPALITY = "municipality"
CONF_PROVINCE = "province"

# --------------------
# Modules
# --------------------

CONF_ENABLE_INCIDENTS = "enable_incidents"

CONF_ENABLE_CHARGING = "enable_charging"
CONF_CHARGING_RADIUS_KM = "charging_radius_km"
CONF_SHOW_ONLY_AVAILABLE = "show_only_available"

# --------------------
# Defaults
# --------------------

DEFAULT_RADIUS_KM = 50
DEFAULT_UPDATE_INTERVAL = 10  # minutes
DEFAULT_MAX_AGE_DAYS = 7
DEFAULT_SCAN_INTERVAL = timedelta(minutes=10)

DEFAULT_CHARGING_RADIUS_KM = 20
DEFAULT_SHOW_ONLY_AVAILABLE = True

# ------DGT INCIDENTS API---------


DGT_REAL_URL = "https://nap.dgt.es/datex2/v3/dgt/SituationPublication/datex2_v36.xml"

DGT_NAMESPACES = {
    "d2": "http://levelC/schema/3/d2Payload",
    "sit": "http://levelC/schema/3/situation",
    "com": "http://levelC/schema/3/common",
    "loc": "http://levelC/schema/3/locationReferencing",
    "cse": "http://levelC/schema/3/commonSpanishExtension",
    "sse": "http://levelC/schema/3/situationSpanishExtension",
    "lse": "http://levelC/schema/3/locationReferencingSpanishExtension",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
}

CATEGORY_MAPPING = {
    "WinterDrivingManagement": "weather",
    "PoorEnvironmentConditions": "weather",
    "RoadOrCarriagewayOrLaneManagement": "roadworks",
    "MaintenanceWorks": "roadworks",
    "Accident": "accident",
    "GeneralObstruction": "obstruction",
    "VehicleObstruction": "obstruction",
    "NonWeatherRelatedRoadConditions": "obstruction",
    "EnvironmentalObstruction": "obstruction",
    "InfrastructureDamageObstruction": "obstruction",
    "SpeedManagement": "restriction",
    "AuthorityOperation": "restriction",
    "GeneralInstructionOrMessageToRoadUsers": "information",
    "AbnormalTraffic": "congestion",
    "TrafficElement": "congestion",
    "GenericSituationRecord": "other",
    "SituationPublication": "other",
}

CAUSE_TRANSLATION = {
    "roadMaintenance": "obras",
    "poorEnvironment": "condiciones meteorológicas",
    "vehicleObstruction": "vehículo obstruyendo",
    "environmentalObstruction": "obstáculo ambiental",
    "obstruction": "obstáculo",
    "infrastructureDamageObstruction": "daño en infraestructura",
    "accident": "accidente",
    "roadOrCarriagewayOrLaneManagement": "gestión de carril",
    "disturbance": "alteración",
    "roadworks": "obras",
    "snowfall": "nieve",
    "snowploughsInUse": "quitanieves activos",
    "badWeather": "mal tiempo",
    "strongWinds": "viento fuerte",
    "rain": "lluvia",
    "frost": "helada",
    "smokeHazard": "humo/peligro",
    "objectOnTheRoad": "objeto en la calzada",
    "obstructionOnTheRoad": "obstrucción en carretera",
    "spillageOnTheRoad": "derrame en carretera",
}

SEVERITY_LEVELS = {
    "low": "low",
    "medium": "medium",
    "high": "high",
    "highest": "highest",
    "veryHigh": "highest",
}

VALIDITY_STATUS = {
    "active": "active",
    "suspended": "suspended",
    "definedByValidityTimeSpec": "active",
}

DESCRIPTION_TEMPLATES = {
    "WinterDrivingManagement": {
        "snowfall": "Nevada en {road}{km_info}{location_info}",
        "snowploughsInUse": "Quitanieves activos en {road}{km_info}{location_info}",
        "frost": "Helada en {road}{km_info}{location_info}",
        "badWeather": "Mal tiempo en {road}{km_info}{location_info}",
        "strongWinds": "Viento fuerte en {road}{km_info}{location_info}",
        "rain": "Lluvia en {road}{km_info}{location_info}",
        "smokeHazard": "Peligro por humo en {road}{km_info}{location_info}",
        "default": "Condiciones invernales en {road}{km_info}{location_info}",
    },
    "PoorEnvironmentConditions": {
        "snowfall": "Nevada en {road}{km_info}{location_info}",
        "badWeather": "Mal tiempo en {road}{km_info}{location_info}",
        "strongWinds": "Viento fuerte en {road}{km_info}{location_info}",
        "rain": "Lluvia en {road}{km_info}{location_info}",
        "frost": "Helada en {road}{km_info}{location_info}",
        "smokeHazard": "Peligro por humo en {road}{km_info}{location_info}",
        "default": "Condiciones adversas en {road}{km_info}{location_info}",
    },
    "RoadOrCarriagewayOrLaneManagement": {
        "roadworks": "Obras en {road}{km_info}{location_info}",
        "default": "Gestión de carril en {road}{km_info}{location_info}",
    },
    "MaintenanceWorks": {
        "roadworks": "Obras de mantenimiento en {road}{km_info}{location_info}",
        "default": "Mantenimiento en {road}{km_info}{location_info}",
    },
    "Accident": {
        "default": "Accidente en {road}{km_info}{location_info}",
    },
    "VehicleObstruction": {
        "default": "Vehículo obstruyendo en {road}{km_info}{location_info}",
    },
    "GeneralObstruction": {
        "objectOnTheRoad": "Objeto en la calzada en {road}{km_info}{location_info}",
        "obstructionOnTheRoad": "Obstrucción en {road}{km_info}{location_info}",
        "spillageOnTheRoad": "Derrame en {road}{km_info}{location_info}",
        "default": "Obstáculo en {road}{km_info}{location_info}",
    },
    "SpeedManagement": {
        "default": "Control de velocidad en {road}{km_info}{location_info}",
    },
    "AbnormalTraffic": {
        "default": "Tráfico anormal en {road}{km_info}{location_info}",
    },
    "default": {
        "default": "Incidente de tráfico en {road}{km_info}{location_info}",
    },
}

# --------ENTITY IDS----------

SENSOR_ENTITY_IDS = {
    "total": "sensor.dgt_total_incidents",
    "weather": "sensor.dgt_weather_incidents",
    "roadworks": "sensor.dgt_roadworks_incidents",
    "accident": "sensor.dgt_accident_incidents",
    "obstruction": "sensor.dgt_obstruction_incidents",
    "congestion": "sensor.dgt_congestion_incidents",
    "restriction": "sensor.dgt_restriction_incidents",
    "information": "sensor.dgt_information_incidents",
    "other": "sensor.dgt_other_incidents",
    "nearest": "sensor.dgt_nearest_incident",
    "list": "sensor.dgt_all_incidents",
}

BINARY_SENSOR_ENTITY_IDS = {
    "weather": "binary_sensor.dgt_has_weather_alerts",
    "roadworks": "binary_sensor.dgt_has_roadworks",
    "accident": "binary_sensor.dgt_has_accidents",
    "obstruction": "binary_sensor.dgt_has_obstructions",
    "any": "binary_sensor.dgt_has_incidents",
}

# -------DGT CHARGING API-------------

DGT_CHARGING_URL = "https://infocar.dgt.es/datex2/v3/miterd/EnergyInfrastructureTablePublication/electrolineras.xml"

DGT_CHARGING_NAMESPACES = {
    "d2": "http://datex2.eu/schema/3/d2Payload",
    "com": "http://datex2.eu/schema/3/common",
    "loc": "http://datex2.eu/schema/3/locationReferencing",
    "egi": "http://datex2.eu/schema/3/energyInfrastructure",
    "fac": "http://datex2.eu/schema/3/facilities",
    "locx": "http://datex2.eu/schema/3/locationExtension",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
}
