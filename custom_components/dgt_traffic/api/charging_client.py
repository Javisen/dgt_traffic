"""DGT Charging API client for electric stations."""

import math
import aiohttp
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import re

from ..const import DGT_CHARGING_URL, DGT_CHARGING_NAMESPACES

_LOGGER = logging.getLogger(__name__)


class DGTChargingClient:
    """Client for DGT Charging Stations API."""

    # CONSTANTES PARA RANGOS DE POTENCIA
    POWER_RANGES = {
        "Lenta (< 22 kW)": (0, 22),
        "Semi-rápida (22-49 kW)": (22, 50),
        "Rápida (50-149 kW)": (50, 150),
        "Ultra rápida (150+ kW)": (150, float("inf")),
    }

    def __init__(self, session: aiohttp.ClientSession):
        """Initialize."""
        self._session = session
        self._cached_stations = []
        self._last_update = None

    async def get_charging_stations(
        self,
        max_age_hours: int = 24,
        only_available: bool = True,
        user_lat: float = None,
        user_lon: float = None,
        radius_km: float = 50.0,
    ) -> List[Dict]:
        """Get charging stations from DGT API con soporte de filtrado."""
        try:
            headers = {
                "User-Agent": "HomeAssistant-DGT-Traffic/1.0",
                "Accept": "application/xml",
            }

            timeout = aiohttp.ClientTimeout(total=90)

            async with self._session.get(
                DGT_CHARGING_URL, headers=headers, timeout=timeout
            ) as response:

                if response.status != 200:
                    _LOGGER.error("DGT Charging API returned %s", response.status)
                    return self._cached_stations or []

                xml_content = await response.text()

                # PASER COORDENADAS
                stations = self._parse_xml(
                    xml_content,
                    max_age_hours,
                    only_available,
                    user_lat=user_lat,
                    user_lon=user_lon,
                    radius_km=radius_km,
                )

                self._cached_stations = stations
                self._last_update = datetime.now()

                return stations or []

        except Exception as err:
            _LOGGER.error("Error en get_charging_stations: %s", err)
            return self._cached_stations or []

    def _parse_xml(
        self,
        xml_content: str,
        max_age_hours: int,
        only_available: bool,
        user_lat: float = None,
        user_lon: float = None,
        radius_km: float = 50.0,
    ) -> List[Dict]:
        """Parse charging stations XML con filtrado por cercanía."""
        import io

        stations = []
        filtered_out = 0
        parsed_count = 0

        # Filtrado de coordenadas
        apply_filter = user_lat is not None and user_lon is not None

        if apply_filter:
            # Margen bounding box
            lat_margin = radius_km / 111.0  # 1 grado ≈ 111km
            lon_margin = radius_km / (111.0 * abs(math.cos(math.radians(user_lat))))

        try:
            # Iterparse
            context = ET.iterparse(
                io.BytesIO(xml_content.encode("utf-8")), events=("start", "end")
            )

            # Raíz
            event, root = next(context)

            for event, elem in context:
                if event == "end" and elem.tag.endswith("energyInfrastructureSite"):
                    station_id = elem.get("id", "unknown")

                    # FILTRO POR CERCANÍA
                    if apply_filter:
                        # Buscar coordenadas
                        lat_elem = elem.find(".//{*}latitude")
                        lon_elem = elem.find(".//{*}longitude")

                        if lat_elem is not None and lon_elem is not None:
                            if lat_elem.text and lon_elem.text:
                                try:
                                    st_lat = float(lat_elem.text.strip())
                                    st_lon = float(lon_elem.text.strip())

                                    # Verificar bounding box
                                    if (
                                        abs(st_lat - user_lat) > lat_margin
                                        or abs(st_lon - user_lon) > lon_margin
                                    ):
                                        filtered_out += 1
                                        root.clear()
                                        continue

                                except (ValueError, TypeError) as e:
                                    filtered_out += 1
                                    root.clear()
                                    continue
                            else:
                                filtered_out += 1
                                root.clear()
                                continue

                    # PARSEO COMPLETO
                    station = self._parse_station_specific(elem)
                    if station:
                        stations.append(station)
                        parsed_count += 1
                    else:
                        filtered_out += 1

                    # LIMPIEZA DE MEMORIA
                    elem.clear()
                    root.clear()

            if apply_filter and parsed_count == 0:
                _LOGGER.warning(
                    "Cero estaciones en el radio. ¿Coordenadas correctas? User: %s,%s",
                    user_lat,
                    user_lon,
                )

        except ET.ParseError as err:
            _LOGGER.error("Error parsing XML: %s", err)
            return []
        except Exception as err:
            _LOGGER.error("Error inesperado en _parse_xml: %s", err)
            return []

        return stations

    def _parse_station_specific(self, station_elem) -> Optional[Dict]:
        """Parse station ESPECÍFICO XML de DGT España."""
        try:
            station_id = station_elem.get("id", "")
            if not station_id:
                return None

            name = f"Estación {station_id}"
            name_elem = station_elem.find(".//{*}name")
            if name_elem is not None:
                value_elem = name_elem.find(".//{*}value[@lang='es']")
                if value_elem is None:
                    value_elem = name_elem.find(".//{*}value")
                if value_elem is not None and value_elem.text:
                    name = value_elem.text.strip()

            coords_elem = station_elem.find(".//{*}coordinatesForDisplay")
            if coords_elem is None:
                lat_elem = station_elem.find(".//{*}latitude")
                lon_elem = station_elem.find(".//{*}longitude")
            else:
                lat_elem = coords_elem.find(".//{*}latitude")
                lon_elem = coords_elem.find(".//{*}longitude")

            if lat_elem is None or lon_elem is None:
                return None

            if lat_elem.text is None or lon_elem.text is None:
                return None

            try:
                lat = float(lat_elem.text.strip())
                lon = float(lon_elem.text.strip())
            except (ValueError, TypeError):
                return None

            operator_elem = station_elem.find(".//{*}operator")
            operator_name = "Desconocido"
            operator_id = ""

            if operator_elem is not None:
                operator_id = operator_elem.get("id", "")
                op_name_elem = operator_elem.find(".//{*}name")
                if op_name_elem is not None:
                    op_value_elem = op_name_elem.find(".//{*}value[@lang='es']")
                    if op_value_elem is None:
                        op_value_elem = op_name_elem.find(".//{*}value")
                    if op_value_elem is not None and op_value_elem.text:
                        operator_name = op_value_elem.text.strip()

                if operator_name == "Desconocido" and operator_id.startswith("ES*"):
                    operator_codes = {
                        "ES*915": "Iberdrola",
                        "ES*920": "Endesa",
                        "ES*925": "Repsol",
                        "ES*930": "Cepsa",
                        "ES*935": "BP",
                        "ES*940": "Shell",
                        "ES*945": "Tesla",
                        "ES*950": "EasyCharger",
                        "ES*955": "Zunder",
                        "ES*960": "Wenea",
                    }
                    operator_name = operator_codes.get(
                        operator_id, f"Operador {operator_id[3:]}"
                    )

            address_parts = []
            for addr_line in station_elem.findall(".//{*}addressLine"):
                text_elem = addr_line.find(".//{*}value[@lang='es']")
                if text_elem is None:
                    text_elem = addr_line.find(".//{*}value")
                if text_elem is not None and text_elem.text:
                    address_parts.append(text_elem.text.strip())

            address = (
                ", ".join(address_parts) if address_parts else "Dirección no disponible"
            )

            charging_points = self._parse_charging_points_robust(station_elem)

            max_power = 0
            total_points = len(charging_points) if charging_points else 1

            if charging_points:
                for point in charging_points:
                    power = point.get("power_kw", 0)
                    if power > max_power:
                        max_power = power

            if max_power == 0:
                refill_points = station_elem.findall(".//{*}refillPoint")
                if refill_points:
                    for refill in refill_points[:3]:
                        power_elem = refill.find(".//{*}ratedOutputPower")
                        if power_elem is not None and power_elem.text:
                            try:
                                power = float(power_elem.text.strip())
                                if power > max_power:
                                    max_power = power
                            except:
                                pass

                if max_power == 0 and charging_points:
                    for point in charging_points:
                        connector_type = point.get("connector_type", "").upper()
                        if "CCS" in connector_type or "COMBO" in connector_type:
                            max_power = max(max_power, 150)
                        elif "CHADEMO" in connector_type:
                            max_power = max(max_power, 50)
                        elif "TYPE 2" in connector_type:
                            max_power = max(max_power, 22)

                if max_power == 0:
                    max_power = 22.0

            station = {
                "id": station_id,
                "name": name,
                "coordinates": {"latitude": lat, "longitude": lon},
                "operator": {"id": operator_id, "name": operator_name},
                "address": address,
                "total_points": total_points,
                "available_points": total_points,  # Asumir todos disponibles
                "max_power_kw": round(max_power, 1),
                "is_available": True,
                "charging_points": charging_points,
                "last_updated": datetime.now().isoformat(),
            }

            station["power_range"] = self._get_power_range_category(max_power)

            return station

        except Exception as err:
            return None

    def _get_power_range_category(self, max_power_kw: float) -> str:
        if max_power_kw < 22:
            return "Lenta (< 22 kW)"
        elif max_power_kw <= 49:
            return "Semi-rápida (22-49 kW)"
        elif max_power_kw <= 149:
            return "Rápida (50-149 kW)"
        else:
            return "Ultra rápida (150+ kW)"

    def _parse_operating_hours_robust(self, station_elem) -> Dict[str, Any]:
        """Parse operating hours - versión robusta."""
        hours_candidates = [
            station_elem.find("fac:operatingHours", DGT_CHARGING_NAMESPACES),
            station_elem.find(".//{*}operatingHours"),
        ]

        hours_elem = None
        for candidate in hours_candidates:
            if candidate is not None:
                hours_elem = candidate
                break

        if hours_elem is None:
            return {"label": "24/7", "always_open": True, "is_open_now": True}

        label = ""
        label_candidates = [
            hours_elem.find("fac:label", DGT_CHARGING_NAMESPACES),
            hours_elem.find(".//{*}label"),
        ]

        for label_elem in label_candidates:
            if label_elem is not None and label_elem.text:
                label = label_elem.text
                break

        is_open_now = self._parse_hours_label(label)
        always_open = "00:00 - 23:59" in label or "24 horas" in label.lower()

        return {
            "label": label,
            "always_open": always_open,
            "is_open_now": is_open_now,
            "parsed_label": label,
        }

    def _parse_hours_label(self, label: str) -> bool:
        """Parse hours label to determine if open now."""
        if not label or "00:00 - 23:59" in label:
            return True

        try:
            now = datetime.now()
            current_weekday = now.strftime("%A").lower()
            current_time = now.strftime("%H:%M")
            spanish_days = {
                "lunes": "monday",
                "martes": "tuesday",
                "miércoles": "wednesday",
                "miercoles": "wednesday",
                "jueves": "thursday",
                "viernes": "friday",
                "sábado": "saturday",
                "sabado": "saturday",
                "domingo": "sunday",
            }

            for esp_day, eng_day in spanish_days.items():
                if (
                    eng_day.lower() == current_weekday
                    and esp_day.lower() in label.lower()
                ):

                    pattern = (
                        rf"{esp_day}\s*\((\d{{2}}:\d{{2}})\s*-\s*(\d{{2}}:\d{{2}})\)"
                    )
                    match = re.search(pattern, label.lower())
                    if match:
                        open_time = match.group(1)
                        close_time = match.group(2)
                        return open_time <= current_time <= close_time

            return False

        except Exception:
            return True

    def _parse_location_robust(self, station_elem) -> Dict[str, Any]:
        """Parse location information - versión robusta."""
        location = {
            "latitude": None,
            "longitude": None,
            "address": {},
            "province": None,
            "municipality": None,
            "autonomous_community": None,
            "postcode": None,
        }

        address_lines = []

        address_line_candidates = [
            station_elem.findall(".//{*}addressLine"),
            station_elem.findall("locx:addressLine", DGT_CHARGING_NAMESPACES),
        ]

        all_address_lines = []
        for candidate in address_line_candidates:
            if candidate:
                all_address_lines.extend(candidate)

        for line_elem in all_address_lines:
            text = None
            text_candidates = [
                line_elem.find(".//{*}value"),
                line_elem.find(
                    "locx:text/com:values/com:value", DGT_CHARGING_NAMESPACES
                ),
            ]

            for text_elem in text_candidates:
                if text_elem is not None and text_elem.text:
                    text = text_elem.text.strip()
                    break

            if text:
                order = line_elem.get("order", "0")
                location["address"][order] = text
                text_lower = text.lower()
                if not any(
                    k in text_lower for k in ("provincia:", "comunidad autónoma:")
                ):
                    address_lines.append(text)

                if "provincia:" in text_lower:
                    location["province"] = text.split(":", 1)[-1].strip()
                elif "municipio:" in text_lower:
                    location["municipality"] = text.split(":", 1)[-1].strip()
                elif "comunidad autónoma:" in text_lower:
                    location["autonomous_community"] = text.split(":", 1)[-1].strip()
                elif text.strip().isdigit() and len(text.strip()) == 5:
                    location["postcode"] = text.strip()

        return location

    def _parse_operator_robust(self, station_elem) -> Dict[str, Any]:
        """Parse operator information"""
        operator_candidates = [
            station_elem.find("fac:operator", DGT_CHARGING_NAMESPACES),
            station_elem.find(".//{*}operator"),
        ]

        operator_elem = None
        for candidate in operator_candidates:
            if candidate is not None:
                operator_elem = candidate
                break

        if operator_elem is None:
            return {"name": "Desconocido", "id": "unknown", "type": "unknown"}

        operator_id = operator_elem.get("id", "")
        operator_name = "Desconocido"
        name_candidates = [
            operator_elem.find(".//{*}name//{*}value"),
            operator_elem.find(
                "fac:name/com:values/com:value", DGT_CHARGING_NAMESPACES
            ),
        ]

        for name_elem in name_candidates:
            if name_elem is not None and name_elem.text:
                operator_name = name_elem.text.strip()
                break

        if operator_name == "Desconocido" and operator_id.startswith("ES*"):
            operator_codes = {
                "ES*915": "Iberdrola",
                "ES*920": "Endesa",
                "ES*925": "Repsol",
                "ES*930": "Cepsa",
                "ES*935": "BP",
                "ES*940": "Shell",
                "ES*945": "Tesla",
                "ES*950": "EasyCharger",
                "ES*955": "Zunder",
                "ES*960": "Wenea",
            }
            operator_name = operator_codes.get(
                operator_id, f"Operador {operator_id[3:]}"
            )

        return {
            "id": operator_id,
            "name": operator_name,
            "type": "public" if "ES*" in operator_id else "private",
        }

    def _parse_charging_points_robust(self, station_elem) -> List[Dict]:
        """Parse ALL charging points sin depender de URLs de Namespace."""
        charging_points = []

        def find_agnostic(element, tag_target):
            for child in element.iter():
                if child.tag.split("}")[-1] == tag_target:
                    return child
            return None

        try:
            all_connectors = [
                node
                for node in station_elem.iter()
                if node.tag.split("}")[-1] == "connector"
            ]

            if not all_connectors:
                return []

            for i, connector_elem in enumerate(all_connectors):
                try:
                    point_id = f"conn_{i}"

                    # --- TIPO Y MODO ---
                    type_el = find_agnostic(connector_elem, "connectorType")
                    mode_el = find_agnostic(connector_elem, "chargingMode")

                    raw_connector = type_el.text if type_el is not None else "unknown"
                    raw_mode = mode_el.text if mode_el is not None else "unknown"

                    raw_upper = raw_connector.upper()
                    if "COMBO" in raw_upper or "CCS" in raw_upper:
                        connector_type = "CCS2"
                    elif "CHADEMO" in raw_upper:
                        connector_type = "CHAdeMO"
                    elif "IEC62196T2" in raw_upper or "TYPE2" in raw_upper:
                        connector_type = "Type 2"
                    else:
                        connector_type = (
                            raw_connector if raw_connector != "unknown" else "Otros"
                        )

                    # --- POTENCIA  ---
                    power_val = 0.0
                    p_el = find_agnostic(connector_elem, "maxPowerAtSocket")
                    if p_el is None:
                        p_el = find_agnostic(connector_elem, "ratedOutputPower")

                    if p_el is not None and p_el.text:
                        try:
                            clean_text = p_el.text.strip().replace(",", ".")
                            power_val = float(clean_text)
                        except ValueError:
                            power_val = 0.0

                    if power_val > 1000:
                        power_kw = power_val / 1000.0
                    elif power_val > 0:
                        power_kw = power_val
                    else:
                        if "CCS" in connector_type or "COMBO" in connector_type:
                            power_kw = 150.0
                        elif "CHAdeMO" in connector_type:
                            power_kw = 50.0
                        elif "Type 2" in connector_type:
                            power_kw = 22.0
                        else:
                            power_kw = 11.0  # Fallback genérico

                    # --- VOLTAJE Y CORRIENTE ---
                    v_el = find_agnostic(connector_elem, "voltage")
                    c_el = find_agnostic(connector_elem, "maximumCurrent")

                    voltage = (
                        float(v_el.text) if v_el is not None and v_el.text else 0.0
                    )
                    current = (
                        float(c_el.text) if c_el is not None and c_el.text else 0.0
                    )

                    if (voltage <= 0 or current <= 0) and power_kw > 0:
                        if "DC" in raw_mode.upper() or connector_type in [
                            "CCS2",
                            "CHAdeMO",
                        ]:
                            voltage = 800 if power_kw > 50 else 400
                        else:
                            voltage = 400  # AC
                        current = (power_kw * 1000) / voltage if voltage > 0 else 32

                    charging_points.append(
                        {
                            "id": point_id,
                            "connector_type": connector_type,
                            "power_kw": round(power_kw, 1),
                            "is_available": True,
                            "voltage_v": int(voltage),
                            "current_a": int(current),
                            "mode": raw_mode,
                        }
                    )

                except Exception:
                    continue

            return charging_points

        except Exception:
            return []

    def _check_availability(self, operating_hours: Dict) -> bool:
        """Check if station is available based on operating hours."""
        if operating_hours.get("always_open", True):
            return True

        return operating_hours.get("is_open_now", True)

    def _format_address(self, location: Dict) -> str:
        """Format address as string."""
        address_parts = []

        address_lines = location.get("address", {})
        for order in sorted(address_lines.keys()):
            address_parts.append(address_lines[order])

        if location.get("municipality"):
            if not any("municipio:" in part.lower() for part in address_parts):
                address_parts.append(f"Municipio: {location['municipality']}")

        if location.get("province"):
            if not any("provincia:" in part.lower() for part in address_parts):
                address_parts.append(f"Provincia: {location['province']}")

        return ", ".join(address_parts) if address_parts else "Dirección no disponible"

    def _is_recent(self, station: Dict, max_age_hours: int) -> bool:
        """Check if station data is recent enough."""
        try:
            last_updated = station.get("last_updated")
            if not last_updated:
                return True  # Sin fecha, asumir válido

            dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
            age_hours = (datetime.now(dt.tzinfo) - dt).total_seconds() / 3600

            return age_hours <= max_age_hours

        except Exception:
            return True

    def _parse_station(self, station_elem) -> Optional[Dict]:
        """Alias para compatibilidad."""
        return self._parse_station_specific(station_elem)
