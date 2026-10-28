"""Meter indexing, querying, filtering, and spatial calculation service."""

import logging
import math
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from app.client.portal_client import PortalClient
from app.config import settings
from app.models.meter import (
    EnergyReading,
    EnergySummary,
    GeoLocation,
    HierarchyLevel,
    MeterDetail,
    MeterHierarchy,
    MeterSummary,
    NearbyMeter,
)
from app.models.transformer import DistributionTransformer

logger = logging.getLogger("urja.service.meters")


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points on the earth in meters."""
    earth_radius_m = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return earth_radius_m * c


class MeterService:
    """Service responsible for indexing, filtering, caching, and querying meters."""

    def __init__(self, client: Optional[PortalClient] = None):
        self.client = client or PortalClient()
        self._lock = threading.RLock()

        # In-memory storage
        self._meters_by_id: Dict[str, Dict[str, Any]] = {}
        self._dts_by_code: Dict[str, Dict[str, Any]] = {}

        # Cache metadata
        self._last_synced_at: float = 0.0
        self._energy_cache: Dict[str, Tuple[float, EnergySummary]] = {}
        self._energy_cache_ttl = 300.0  # 5 minutes

    @property
    def is_cache_stale(self) -> bool:
        """Check if cached meter dataset has exceeded TTL."""
        if not self._last_synced_at:
            return True
        return (time.time() - self._last_synced_at) > settings.cache_ttl_seconds

    @property
    def cache_age_seconds(self) -> Optional[float]:
        """Return elapsed seconds since last sync, or None if never synced."""
        if not self._last_synced_at:
            return None
        return max(0.0, time.time() - self._last_synced_at)

    def sync_all(self, force: bool = False) -> Dict[str, int]:
        """Perform a full synchronization from the Urja Meter Ops upstream portal.

        Uses the HMAC-signed bulk export endpoint to fetch all meters in one call,
        then fetches all Distribution Transformers.
        """
        with self._lock:
            if not force and not self.is_cache_stale:
                return {
                    "meters_synced": len(self._meters_by_id),
                    "transformers_synced": len(self._dts_by_code),
                }

            logger.info("Initiating full synchronization with Urja Meter Ops...")
            start_time = time.time()

            # 1. Fetch DTs
            raw_dts = self.client.fetch_all_dts()
            dts_map: Dict[str, Dict[str, Any]] = {}
            for dt in raw_dts:
                code = dt.get("code")
                if code:
                    dts_map[code] = {
                        "code": code,
                        "name": dt.get("name", ""),
                        "feederCode": dt.get("feederCode", ""),
                        "capacityKva": float(dt.get("capacityKva", 0.0)),
                    }

            # 2. Fetch all meters via signed export
            export_result = self.client.fetch_all_meters_export(page=1)
            raw_meters = export_result.get("data", [])

            meters_map: Dict[str, Dict[str, Any]] = {}
            for item in raw_meters:
                meter_id = item.get("meterId")
                if meter_id:
                    meters_map[meter_id] = item

            # Atomic swap of indices
            self._dts_by_code = dts_map
            self._meters_by_id = meters_map
            self._last_synced_at = time.time()

            duration = self._last_synced_at - start_time
            logger.info(
                "Sync complete in %.2fs: %d meters, %d distribution transformers indexed.",
                duration,
                len(self._meters_by_id),
                len(self._dts_by_code),
            )

            return {
                "meters_synced": len(self._meters_by_id),
                "transformers_synced": len(self._dts_by_code),
            }

    def _ensure_synced(self) -> None:
        """Synchronize on demand if dataset is uninitialized or stale."""
        if not self._meters_by_id or self.is_cache_stale:
            self.sync_all()

    def _to_meter_summary(self, item: Dict[str, Any]) -> MeterSummary:
        """Convert a normalized raw meter record to a MeterSummary model."""
        geo_dict = item.get("geo")
        geo_model = None
        if geo_dict and "lat" in geo_dict and "lng" in geo_dict:
            geo_model = GeoLocation(
                latitude=float(geo_dict["lat"]),
                longitude=float(geo_dict["lng"]),
            )

        return MeterSummary(
            meter_id=item["meterId"],
            serial_no=item.get("serialNo", ""),
            make=item.get("make", ""),
            phase_type=item.get("phaseType", ""),
            install_status=item.get("installStatus", ""),
            install_type=item.get("installType"),
            build=item.get("build"),
            dt_code=item.get("dtCode", ""),
            geo=geo_model,
        )

    def _to_meter_detail(self, item: Dict[str, Any], latest_reading: Optional[EnergyReading] = None) -> MeterDetail:
        """Convert a normalized raw meter record to a comprehensive MeterDetail model."""
        summary = self._to_meter_summary(item)
        raw_h = item.get("hierarchy", {})

        def parse_level(key: str) -> Optional[HierarchyLevel]:
            val = raw_h.get(key)
            if isinstance(val, dict) and "name" in val and "code" in val:
                return HierarchyLevel(name=val["name"], code=val["code"])
            return None

        hierarchy = MeterHierarchy(
            zone=parse_level("zone"),
            circle=parse_level("circle"),
            division=parse_level("division"),
            subdivision=parse_level("subdivision"),
            substation=parse_level("substation"),
            feeder=parse_level("feeder"),
            dt=parse_level("dt"),
        )

        return MeterDetail(
            **summary.model_dump(),
            hierarchy=hierarchy,
            latest_reading=latest_reading,
        )

    def get_meter_by_id(self, meter_id: str) -> Optional[MeterDetail]:
        """Retrieve a single meter by identifier with detailed hierarchy and telemetry."""
        self._ensure_synced()
        item = self._meters_by_id.get(meter_id)
        if not item:
            return None

        # Fetch latest reading if available
        latest_reading = None
        try:
            energy_summary = self.get_meter_energy(meter_id)
            latest_reading = energy_summary.latest_reading
        except Exception as exc:
            logger.debug("Failed to retrieve telemetry for meter %s: %s", meter_id, exc)

        return self._to_meter_detail(item, latest_reading=latest_reading)

    def query_meters(
        self,
        query: Optional[str] = None,
        make: Optional[str] = None,
        phase_type: Optional[str] = None,
        install_status: Optional[str] = None,
        dt_code: Optional[str] = None,
        feeder_code: Optional[str] = None,
        zone_code: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[MeterSummary], int]:
        """Filter and search meters across multiple attributes with pagination.

        Supports case-insensitive full-text substring matching on meter ID or hardware serial,
        plus exact match filtering on make, phase, status, DT, feeder, and zone.
        """
        self._ensure_synced()

        filtered: List[Dict[str, Any]] = []
        normalized_q = query.strip().lower() if query else None
        normalized_make = make.strip().lower() if make else None
        normalized_phase = phase_type.strip().lower() if phase_type else None
        normalized_status = install_status.strip().lower() if install_status else None
        normalized_dt = dt_code.strip().upper() if dt_code else None
        normalized_feeder = feeder_code.strip().upper() if feeder_code else None
        normalized_zone = zone_code.strip().upper() if zone_code else None

        for item in self._meters_by_id.values():
            # Query match on meterId or serialNo
            if normalized_q:
                m_id = item.get("meterId", "").lower()
                s_no = item.get("serialNo", "").lower()
                if normalized_q not in m_id and normalized_q not in s_no:
                    continue

            # Exact filters
            if normalized_make and item.get("make", "").lower() != normalized_make:
                continue

            if normalized_phase and item.get("phaseType", "").lower() != normalized_phase:
                continue

            if normalized_status and item.get("installStatus", "").lower() != normalized_status:
                continue

            if normalized_dt and item.get("dtCode", "").upper() != normalized_dt:
                continue

            # Hierarchy filters
            h = item.get("hierarchy", {})
            if normalized_feeder:
                feeder_c = h.get("feeder", {}).get("code", "").upper()
                if feeder_c != normalized_feeder:
                    continue

            if normalized_zone:
                zone_c = h.get("zone", {}).get("code", "").upper()
                if zone_c != normalized_zone:
                    continue

            filtered.append(item)

        total_count = len(filtered)
        paginated_items = filtered[skip : skip + limit]
        return [self._to_meter_summary(x) for x in paginated_items], total_count

    def find_nearby_meters(
        self,
        latitude: float,
        longitude: float,
        radius_meters: float = 5000.0,
        limit: int = 20,
    ) -> List[NearbyMeter]:
        """Find smart meters within a geographic radius (in meters) of a target coordinate."""
        self._ensure_synced()

        results: List[NearbyMeter] = []
        for item in self._meters_by_id.values():
            geo = item.get("geo")
            if not geo or "lat" not in geo or "lng" not in geo:
                continue

            m_lat = float(geo["lat"])
            m_lng = float(geo["lng"])
            dist_m = haversine_distance_meters(latitude, longitude, m_lat, m_lng)

            if dist_m <= radius_meters:
                summary = self._to_meter_summary(item)
                results.append(
                    NearbyMeter(
                        meter=summary,
                        distance_meters=round(dist_m, 2),
                        distance_km=round(dist_m / 1000.0, 3),
                    )
                )

        # Sort closest first
        results.sort(key=lambda x: x.distance_meters)
        return results[:limit]

    def get_meter_energy(self, meter_id: str) -> EnergySummary:
        """Fetch and analyze time-series energy intervals for a meter.

        Calculates aggregate active energy consumption delta, voltage stats,
        and flags voltage anomalies (outside nominal 210V - 250V).
        """
        # Check cache
        now = time.time()
        if meter_id in self._energy_cache:
            cached_at, cached_summary = self._energy_cache[meter_id]
            if (now - cached_at) < self._energy_cache_ttl:
                return cached_summary

        raw_result = self.client.fetch_meter_energy(meter_id)
        raw_readings = raw_result.get("data", [])

        parsed_readings: List[EnergyReading] = []
        voltages: List[float] = []

        for r in raw_readings:
            try:
                kwh_val = float(r.get("kwh", 0.0))
                kvah_val = float(r.get("kvah", 0.0))
                volt_val = float(r.get("voltR", 0.0))
                pf = round(kwh_val / kvah_val, 3) if kvah_val > 0 else None

                parsed_readings.append(
                    EnergyReading(
                        timestamp=r.get("timestamp", ""),
                        kwh=kwh_val,
                        kvah=kvah_val,
                        volt_r=volt_val,
                        power_factor=pf,
                    )
                )
                if volt_val > 0:
                    voltages.append(volt_val)
            except (ValueError, TypeError):
                continue

        reading_count = len(parsed_readings)
        oldest = parsed_readings[0] if reading_count > 0 else None
        latest = parsed_readings[-1] if reading_count > 0 else None

        kwh_delta = None
        if oldest and latest and latest.kwh >= oldest.kwh:
            kwh_delta = round(latest.kwh - oldest.kwh, 2)

        avg_v = round(sum(voltages) / len(voltages), 1) if voltages else None
        min_v = min(voltages) if voltages else None
        max_v = max(voltages) if voltages else None

        has_voltage_anomaly = False
        if voltages and (min_v < 210.0 or max_v > 250.0):
            has_voltage_anomaly = True

        summary = EnergySummary(
            meter_id=meter_id,
            reading_count=reading_count,
            oldest_reading=oldest,
            latest_reading=latest,
            total_active_kwh_delta=kwh_delta,
            avg_voltage_r=avg_v,
            min_voltage_r=min_v,
            max_voltage_r=max_v,
            voltage_anomaly=has_voltage_anomaly,
            readings=parsed_readings,
        )

        self._energy_cache[meter_id] = (now, summary)
        return summary

    def get_meter_geo(self, meter_id: str) -> Optional[GeoLocation]:
        """Fetch geographic location for a meter."""
        self._ensure_synced()
        item = self._meters_by_id.get(meter_id)
        if item and item.get("geo"):
            geo = item["geo"]
            return GeoLocation(latitude=float(geo["lat"]), longitude=float(geo["lng"]))

        # Fallback to direct client call if not in export
        raw_geo = self.client.fetch_meter_geo(meter_id)
        data = raw_geo.get("data", {})
        if "latitude" in data and "longitude" in data:
            return GeoLocation(
                latitude=float(data["latitude"]),
                longitude=float(data["longitude"]),
            )
        return None

    def get_all_raw_meters(self) -> List[Dict[str, Any]]:
        """Return all raw normalized meter records (for hierarchy/transformer services)."""
        self._ensure_synced()
        return list(self._meters_by_id.values())

    def get_all_raw_dts(self) -> List[Dict[str, Any]]:
        """Return all raw DT records."""
        self._ensure_synced()
        return list(self._dts_by_code.values())
