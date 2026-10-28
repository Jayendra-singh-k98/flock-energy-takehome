"""Data models for utility fleet analytics and grid health indicators."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class FleetOverview(BaseModel):
    """Aggregate breakdown of the smart meter fleet across hardware, phase, and status."""

    total_meters: int = Field(..., description="Total smart meters tracked")
    total_transformers: int = Field(..., description="Total distribution transformers")
    total_transformer_capacity_kva: float = Field(..., description="Summed capacity of all DTs in kVA")
    avg_meters_per_transformer: float = Field(..., description="Average number of meters fed per transformer")

    status_distribution: Dict[str, int] = Field(..., description="Count of meters by operational status")
    make_distribution: Dict[str, int] = Field(..., description="Count of meters by hardware vendor")
    phase_distribution: Dict[str, int] = Field(..., description="Count of meters by electrical phase")
    build_distribution: Dict[str, int] = Field(..., description="Count of meters by protocol/build generation")
    install_type_distribution: Dict[str, int] = Field(..., description="Count of meters by installation category")


class VoltageAnomalyItem(BaseModel):
    """A meter identified with unusual voltage conditions."""

    meter_id: str
    status: str
    make: str
    dt_code: str
    latest_voltage: Optional[float]
    anomaly_type: str  # "UNDER_VOLTAGE" (< 210V), "OVER_VOLTAGE" (> 250V)


class FleetAnomalies(BaseModel):
    """Summary of fleet operational anomalies requiring attention."""

    faulty_meter_count: int
    decommissioned_meter_count: int
    voltage_anomaly_count: int
    faulty_meter_ids: List[str]
    voltage_anomalies: List[VoltageAnomalyItem]
