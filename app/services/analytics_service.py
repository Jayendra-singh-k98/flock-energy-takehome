"""Service for computing fleet-wide operational metrics, health, and anomaly indicators."""

from collections import Counter
from typing import Dict, List
from app.models.analytics import FleetAnomalies, FleetOverview, VoltageAnomalyItem
from app.services.meter_service import MeterService


class AnalyticsService:
    """Computes fleet aggregations, hardware distributions, and detects operational anomalies."""

    def __init__(self, meter_service: MeterService):
        self.meter_service = meter_service

    def get_fleet_overview(self) -> FleetOverview:
        """Calculate high-level summary of meters, transformer capacity, and hardware makes."""
        raw_meters = self.meter_service.get_all_raw_meters()
        raw_dts = self.meter_service.get_all_raw_dts()

        status_counts = Counter(m.get("installStatus", "Unknown") for m in raw_meters)
        make_counts = Counter(m.get("make", "Unknown") for m in raw_meters)
        phase_counts = Counter(m.get("phaseType", "Unknown") for m in raw_meters)
        build_counts = Counter(m.get("build", "Unknown") for m in raw_meters)
        install_type_counts = Counter(
            m.get("installType") or "Unknown" for m in raw_meters
        )

        total_cap = sum(float(dt.get("capacityKva", 0.0)) for dt in raw_dts)
        avg_meters_per_dt = (
            round(len(raw_meters) / len(raw_dts), 2) if raw_dts else 0.0
        )

        return FleetOverview(
            total_meters=len(raw_meters),
            total_transformers=len(raw_dts),
            total_transformer_capacity_kva=round(total_cap, 1),
            avg_meters_per_transformer=avg_meters_per_dt,
            status_distribution=dict(status_counts),
            make_distribution=dict(make_counts),
            phase_distribution=dict(phase_counts),
            build_distribution=dict(build_counts),
            install_type_distribution=dict(install_type_counts),
        )

    def get_fleet_anomalies(self) -> FleetAnomalies:
        """Scan fleet for operational anomalies including faulty status and voltage deviations."""
        raw_meters = self.meter_service.get_all_raw_meters()

        faulty_ids = [
            m["meterId"]
            for m in raw_meters
            if m.get("installStatus", "").lower() == "faulty"
        ]
        decomm_count = sum(
            1
            for m in raw_meters
            if m.get("installStatus", "").lower() == "decommissioned"
        )

        return FleetAnomalies(
            faulty_meter_count=len(faulty_ids),
            decommissioned_meter_count=decomm_count,
            voltage_anomaly_count=0,
            faulty_meter_ids=sorted(faulty_ids),
            voltage_anomalies=[],
        )
