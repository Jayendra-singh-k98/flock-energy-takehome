"""Service for Distribution Transformer queries, asset loading, and aggregation."""

from collections import defaultdict
from typing import Dict, List, Optional
from app.models.meter import MeterSummary
from app.models.transformer import DistributionTransformer, TransformerDetail
from app.services.meter_service import MeterService


class TransformerService:
    """Service providing Distribution Transformer (DT) lookups and connected load statistics."""

    def __init__(self, meter_service: MeterService):
        self.meter_service = meter_service

    def _build_dt_meter_buckets(self) -> Dict[str, List[MeterSummary]]:
        """Group all current meters by their assigned DT code."""
        buckets: Dict[str, List[MeterSummary]] = defaultdict(list)
        raw_meters = self.meter_service.get_all_raw_meters()
        for raw in raw_meters:
            dt_code = raw.get("dtCode")
            if dt_code:
                summary = self.meter_service._to_meter_summary(raw)
                buckets[dt_code].append(summary)
        return buckets

    def list_transformers(
        self, feeder_code: Optional[str] = None
    ) -> List[DistributionTransformer]:
        """List all Distribution Transformers with dynamic connected meter asset counts."""
        raw_dts = self.meter_service.get_all_raw_dts()
        buckets = self._build_dt_meter_buckets()

        transformers: List[DistributionTransformer] = []
        normalized_feeder = feeder_code.strip().upper() if feeder_code else None

        for dt in raw_dts:
            dt_feeder = dt.get("feederCode", "")
            if normalized_feeder and dt_feeder.upper() != normalized_feeder:
                continue

            dt_code = dt["code"]
            meters = buckets.get(dt_code, [])

            installed_count = sum(1 for m in meters if m.install_status.lower() == "installed")
            faulty_count = sum(1 for m in meters if m.install_status.lower() == "faulty")
            decomm_count = sum(1 for m in meters if m.install_status.lower() == "decommissioned")

            transformers.append(
                DistributionTransformer(
                    code=dt_code,
                    name=dt.get("name", dt_code),
                    feeder_code=dt_feeder,
                    capacity_kva=float(dt.get("capacityKva", 0.0)),
                    connected_meters_count=len(meters),
                    installed_meters_count=installed_count,
                    faulty_meters_count=faulty_count,
                    decommissioned_meters_count=decomm_count,
                )
            )

        # Sort by code
        transformers.sort(key=lambda x: x.code)
        return transformers

    def get_transformer_detail(self, code: str) -> Optional[TransformerDetail]:
        """Retrieve a specific Distribution Transformer and all connected meters."""
        normalized_code = code.strip().upper()
        raw_dts = self.meter_service.get_all_raw_dts()
        dt = next((d for d in raw_dts if d["code"].upper() == normalized_code), None)
        if not dt:
            return None

        buckets = self._build_dt_meter_buckets()
        meters = buckets.get(dt["code"], [])

        installed_count = sum(1 for m in meters if m.install_status.lower() == "installed")
        faulty_count = sum(1 for m in meters if m.install_status.lower() == "faulty")
        decomm_count = sum(1 for m in meters if m.install_status.lower() == "decommissioned")

        return TransformerDetail(
            code=dt["code"],
            name=dt.get("name", dt["code"]),
            feeder_code=dt.get("feederCode", ""),
            capacity_kva=float(dt.get("capacityKva", 0.0)),
            connected_meters_count=len(meters),
            installed_meters_count=installed_count,
            faulty_meters_count=faulty_count,
            decommissioned_meters_count=decomm_count,
            connected_meters=meters,
        )
