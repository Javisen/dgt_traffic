"""DGT API client for Datex2 v3.6."""

import aiohttp
import asyncio
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from zoneinfo import ZoneInfo

from ..const import (
    DGT_REAL_URL,
    DGT_NAMESPACES,
    CATEGORY_MAPPING,
    CAUSE_TRANSLATION,
    SEVERITY_LEVELS,
    VALIDITY_STATUS,
    DESCRIPTION_TEMPLATES,
)

_LOGGER = logging.getLogger(__name__)


class DGTClient:
    """Client for DGT Datex2 v3.6 API."""

    def __init__(self, session: aiohttp.ClientSession):
        """Initialize."""
        self._session = session
        self._cached_incidents = []
        self._last_update = None
        self._xml_parser = DGTXMLParser()

    async def get_incidents(self, max_age_days: int = 7) -> List[Dict]:
        """Get traffic incidents from DGT API."""
        try:
            headers = {
                "User-Agent": "HomeAssistant-DGT-Traffic/1.0",
                "Accept": "application/xml",
            }

            async with self._session.get(
                DGT_REAL_URL, headers=headers, timeout=60
            ) as response:

                if response.status != 200:
                    _LOGGER.error("DGT API returned %s", response.status)
                    return self._cached_incidents

                xml_content = await response.text()

                incidents = await self._xml_parser.parse_xml(
                    xml_content, max_age_days=max_age_days
                )

                self._cached_incidents = incidents
                self._last_update = datetime.now()

                _LOGGER.info("Found %s valid incidents", len(incidents))
                return incidents

        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.warning("Error fetching DGT data: %s", err)
            return self._cached_incidents
        except Exception as err:
            _LOGGER.error("Unexpected error: %s", err)
            return []


class DGTXMLParser:
    """Parser for Datex2 v3.6 XML format."""

    def __init__(self):
        """Initialize parser."""
        self._timezone = ZoneInfo("Europe/Madrid")
        self._severity_map = {
            "highest": "high",
            "high": "high",
            "medium": "medium",
            "low": "low",
        }

    async def parse_xml(self, xml_content: str, max_age_days: int = 7) -> List[Dict]:
        """Parse XML content and extract incidents."""
        incidents = []

        try:
            root = ET.fromstring(xml_content)

            for prefix, uri in DGT_NAMESPACES.items():
                ET.register_namespace(prefix, uri)

            situations = root.findall(".//sit:situation", DGT_NAMESPACES)

            for situation in situations:
                incident = self._parse_situation(situation)
                if incident and self._is_recent(incident, max_age_days):
                    incidents.append(incident)

        except ET.ParseError as err:
            _LOGGER.error("Error parsing XML: %s", err)
            incidents = await self._parse_with_regex(xml_content, max_age_days)
        except Exception as err:
            _LOGGER.error("Error in XML parsing: %s", err)

        return incidents

    def _parse_situation(self, situation_elem) -> Optional[Dict]:
        """Parse a single situation element."""
        try:
            sit_id = situation_elem.get("id", "unknown")

            overall_severity_elem = situation_elem.find(
                "sit:overallSeverity", DGT_NAMESPACES
            )

            if overall_severity_elem is not None and overall_severity_elem.text:
                overall_severity_raw = overall_severity_elem.text
            else:
                overall_severity_raw = "low"

            overall_severity = self._severity_map.get(
                overall_severity_raw, overall_severity_raw
            )

            record_elem = situation_elem.find("sit:situationRecord", DGT_NAMESPACES)
            if record_elem is None:
                return None

            record_data = self._parse_situation_record(record_elem)
            if not record_data:
                return None

            description = self._generate_description(record_data)

            category = CATEGORY_MAPPING.get(record_data["record_type"], "other")

            severity = record_data.get("severity", overall_severity)

            incident = {
                "id": f"{sit_id}_{record_data['record_id']}",
                "situation_id": sit_id,
                "record_id": record_data["record_id"],
                "version": record_data.get("version", "1"),
                "description": description,
                "type": category,
                "record_type": record_data["record_type"],
                "cause_type": record_data.get("cause_type", ""),
                "detailed_cause": record_data.get("detailed_cause", ""),
                "severity": severity,
                "overall_severity": overall_severity,
                "probability": record_data.get("probability", "certain"),
                "validity_status": record_data.get("validity_status", "active"),
                "creation_time": record_data.get("creation_time"),
                "version_time": record_data.get("version_time"),
                "validity_start": record_data.get("validity_start"),
                "source": record_data.get("source", "DGT"),
                "location": record_data.get("location", {}),
                "latitude": record_data.get("location", {}).get("latitude"),
                "longitude": record_data.get("location", {}).get("longitude"),
                "road": record_data.get("location", {}).get("road"),
                "km_from": record_data.get("location", {}).get("km_from"),
                "km_to": record_data.get("location", {}).get("km_to"),
                "province": record_data.get("location", {}).get("province"),
                "municipality": record_data.get("location", {}).get("municipality"),
                "autonomous_community": record_data.get("location", {}).get(
                    "autonomous_community"
                ),
                "direction": record_data.get("location", {}).get("direction"),
                "lanes_affected": record_data.get("lanes_affected", ""),
                "vehicle_type": record_data.get("vehicle_type", "anyVehicle"),
                "confidence": 1.0,
                "parsed_at": datetime.now().isoformat(),
            }

            return incident

        except Exception:
            return None

    def _parse_situation_record(self, record_elem) -> Optional[Dict]:
        """Parse a situation record element."""
        try:
            record_data = {}

            record_data["record_id"] = record_elem.get("id", "unknown")
            record_data["version"] = record_elem.get("version", "1")

            record_type = record_elem.get(f'{{{DGT_NAMESPACES["xsi"]}}}type', "")
            if ":" in record_type:
                record_data["record_type"] = record_type.split(":")[-1]
            else:
                record_data["record_type"] = record_type

            creation_elem = record_elem.find(
                "sit:situationRecordCreationTime", DGT_NAMESPACES
            )
            if creation_elem is not None and creation_elem.text:
                record_data["creation_time"] = self._parse_datetime(creation_elem.text)

            version_elem = record_elem.find(
                "sit:situationRecordVersionTime", DGT_NAMESPACES
            )
            if version_elem is not None and version_elem.text:
                record_data["version_time"] = self._parse_datetime(version_elem.text)

            severity_elem = record_elem.find("sit:severity", DGT_NAMESPACES)
            if severity_elem is not None and severity_elem.text:
                severity_raw = severity_elem.text
                record_data["severity"] = self._severity_map.get(
                    severity_raw, severity_raw
                )

            prob_elem = record_elem.find("sit:probabilityOfOccurrence", DGT_NAMESPACES)
            if prob_elem is not None and prob_elem.text:
                record_data["probability"] = prob_elem.text

            source_elem = record_elem.find(
                ".//com:sourceIdentification", DGT_NAMESPACES
            )
            if source_elem is not None and source_elem.text:
                record_data["source"] = source_elem.text

            validity_elem = record_elem.find("sit:validity", DGT_NAMESPACES)
            if validity_elem is not None:
                status_elem = validity_elem.find("com:validityStatus", DGT_NAMESPACES)
                if status_elem is not None and status_elem.text:
                    record_data["validity_status"] = VALIDITY_STATUS.get(
                        status_elem.text, status_elem.text
                    )

                start_elem = validity_elem.find(
                    ".//com:overallStartTime", DGT_NAMESPACES
                )
                if start_elem is not None and start_elem.text:
                    record_data["validity_start"] = self._parse_datetime(
                        start_elem.text
                    )

            cause_elem = record_elem.find("sit:cause", DGT_NAMESPACES)
            if cause_elem is not None:
                cause_type_elem = cause_elem.find("sit:causeType", DGT_NAMESPACES)
                if cause_type_elem is not None and cause_type_elem.text:
                    record_data["cause_type"] = cause_type_elem.text

                detailed_elem = cause_elem.find(
                    ".//sit:roadMaintenanceType", DGT_NAMESPACES
                )
                if detailed_elem is None:
                    detailed_elem = cause_elem.find(
                        ".//sit:poorEnvironmentType", DGT_NAMESPACES
                    )
                if detailed_elem is None:
                    detailed_elem = cause_elem.find(
                        ".//sit:accidentType", DGT_NAMESPACES
                    )
                if detailed_elem is None:
                    detailed_elem = cause_elem.find(
                        ".//sit:obstructionType", DGT_NAMESPACES
                    )

                if detailed_elem is not None and detailed_elem.text:
                    record_data["detailed_cause"] = detailed_elem.text

            location = self._extract_location(record_elem)
            record_data["location"] = location

            lanes_elem = record_elem.find(".//loc:laneUsage", DGT_NAMESPACES)
            if lanes_elem is not None and lanes_elem.text:
                record_data["lanes_affected"] = lanes_elem.text

            vehicle_elem = record_elem.find(".//com:vehicleType", DGT_NAMESPACES)
            if vehicle_elem is not None and vehicle_elem.text:
                record_data["vehicle_type"] = vehicle_elem.text

            return record_data

        except Exception:
            return None

    def _extract_location(self, record_elem) -> Dict:
        """Extract location information."""
        location = {}

        try:
            road_elem = record_elem.find(".//loc:roadName", DGT_NAMESPACES)
            if road_elem is not None and road_elem.text:
                location["road"] = road_elem.text

            from_km = record_elem.find(
                ".//loc:from//lse:kilometerPoint", DGT_NAMESPACES
            )
            if from_km is not None and from_km.text:
                location["km_from"] = from_km.text

            to_km = record_elem.find(".//loc:to//lse:kilometerPoint", DGT_NAMESPACES)
            if to_km is not None and to_km.text:
                location["km_to"] = to_km.text

            from_lat = record_elem.find(".//loc:from//loc:latitude", DGT_NAMESPACES)
            from_lon = record_elem.find(".//loc:from//loc:longitude", DGT_NAMESPACES)

            if (
                from_lat is not None
                and from_lat.text
                and from_lon is not None
                and from_lon.text
            ):
                try:
                    location["latitude"] = float(from_lat.text)
                    location["longitude"] = float(from_lon.text)
                except (ValueError, TypeError):
                    pass

            to_lat = record_elem.find(".//loc:to//loc:latitude", DGT_NAMESPACES)
            to_lon = record_elem.find(".//loc:to//loc:longitude", DGT_NAMESPACES)

            if (
                to_lat is not None
                and to_lat.text
                and to_lon is not None
                and to_lon.text
            ):
                try:
                    location["latitude_to"] = float(to_lat.text)
                    location["longitude_to"] = float(to_lon.text)
                except (ValueError, TypeError):
                    pass

            prov_elem = record_elem.find(".//lse:province", DGT_NAMESPACES)
            if prov_elem is not None and prov_elem.text:
                location["province"] = prov_elem.text

            mun_elem = record_elem.find(".//lse:municipality", DGT_NAMESPACES)
            if mun_elem is not None and mun_elem.text:
                location["municipality"] = mun_elem.text

            comm_elem = record_elem.find(".//lse:autonomousCommunity", DGT_NAMESPACES)
            if comm_elem is not None and comm_elem.text:
                location["autonomous_community"] = comm_elem.text

            direction_elem = record_elem.find(
                ".//lse:tpegDirectionRoad", DGT_NAMESPACES
            )
            if direction_elem is not None and direction_elem.text:
                location["direction"] = direction_elem.text
            else:
                tpeg_dir = record_elem.find(".//loc:tpegDirection", DGT_NAMESPACES)
                if tpeg_dir is not None and tpeg_dir.text:
                    location["direction"] = tpeg_dir.text

        except Exception:
            pass

        return location

    def _generate_description(self, record_data: Dict) -> str:
        """Generate human-readable description."""
        try:
            record_type = record_data.get("record_type", "default")
            detailed_cause = record_data.get("detailed_cause", "default")
            location = record_data.get("location", {})

            templates = DESCRIPTION_TEMPLATES.get(
                record_type, DESCRIPTION_TEMPLATES["default"]
            )
            template = templates.get(
                detailed_cause,
                templates.get("default", "{road}{km_info}{location_info}"),
            )

            road = location.get("road", "carretera")

            km_from = location.get("km_from")
            km_to = location.get("km_to")
            km_info = ""
            if km_from and km_to and km_from != km_to:
                km_info = f" entre km {km_from} y {km_to}"
            elif km_from:
                km_info = f" a la altura del km {km_from}"

            municipality = location.get("municipality")
            province = location.get("province")
            location_info = ""
            if municipality and province:
                location_info = f" ({municipality}, {province})"
            elif province:
                location_info = f" ({province})"

            description = template.format(
                road=road,
                km_info=km_info,
                location_info=location_info,
                cause=CAUSE_TRANSLATION.get(detailed_cause, detailed_cause),
                severity=record_data.get("severity", ""),
            )

            if description and description[0].islower():
                description = description[0].upper() + description[1:]

            return description

        except Exception:
            return "Incidente de tráfico"

    def _parse_datetime(self, dt_str: str) -> Optional[str]:
        """Parse datetime string to ISO format."""
        try:
            formats = [
                "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%d %H:%M:%S",
            ]

            for fmt in formats:
                try:
                    dt = datetime.strptime(dt_str, fmt)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=self._timezone)
                    return dt.isoformat()
                except ValueError:
                    continue

            return dt_str

        except Exception:
            return dt_str

    def _is_recent(self, incident: Dict, max_age_days: int) -> bool:
        """Check if incident is recent enough."""
        try:
            creation_time = incident.get("creation_time")
            if not creation_time:
                return True

            if isinstance(creation_time, str):
                try:
                    dt = datetime.fromisoformat(creation_time.replace("Z", "+00:00"))
                except ValueError:
                    return True

            if isinstance(creation_time, datetime):
                age = datetime.now(self._timezone) - creation_time
                return age.days <= max_age_days

            return True

        except Exception:
            return True

    async def _parse_with_regex(
        self, xml_content: str, max_age_days: int
    ) -> List[Dict]:
        """Fallback regex parsing if ElementTree fails."""
        incidents = []

        try:
            sit_pattern = r'<sit:situation[^>]*id="([^"]+)"[^>]*>.*?</sit:situation>'
            situations = re.findall(sit_pattern, xml_content, re.DOTALL)

        except Exception as err:
            _LOGGER.error("Regex parsing failed: %s", err)

        return incidents
