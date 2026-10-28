"""Pydantic data models for smart meters and energy measurements."""

from typing import List, Optional
from pydantic import BaseModel, Field


class GeoLocation(BaseModel):
    """Geographic coordinates for a smart meter."""

    latitude: float = Field(..., description="Latitude in decimal degrees", examples=[26.938961])
    longitude: float = Field(..., description="Longitude in decimal degrees", examples=[75.830956])


class HierarchyLevel(BaseModel):
    """A single tier in the electrical distribution hierarchy."""

    name: str = Field(..., description="Human-readable name of the hierarchy node", examples=["Jaipur Zone 1"])
    code: str = Field(..., description="Identifier code of the hierarchy node", examples=["Z-01"])


class MeterHierarchy(BaseModel):
    """Complete distribution network hierarchy path for a meter."""

    zone: Optional[HierarchyLevel] = Field(None, description="Administrative Zone")
    circle: Optional[HierarchyLevel] = Field(None, description="Administrative Circle")
    division: Optional[HierarchyLevel] = Field(None, description="Operational Division")
    subdivision: Optional[HierarchyLevel] = Field(None, description="Subdivision tier")
    substation: Optional[HierarchyLevel] = Field(None, description="Substation feeding this section")
    feeder: Optional[HierarchyLevel] = Field(None, description="Feeder line")
    dt: Optional[HierarchyLevel] = Field(None, description="Distribution Transformer")


class EnergyReading(BaseModel):
    """Single time-series interval reading from a smart meter."""

    timestamp: str = Field(..., description="Timestamp of interval reading (DD/MM/YYYY HH:MM)", examples=["24/06/2026 00:00"])
    kwh: float = Field(..., description="Cumulative active energy in kilowatt-hours", examples=[48439.16])
    kvah: float = Field(..., description="Cumulative apparent energy in kilovolt-ampere hours", examples=[52314.29])
    volt_r: float = Field(..., description="Phase R RMS Voltage in Volts", examples=[229.0])
    power_factor: Optional[float] = Field(None, description="Estimated power factor (active / apparent energy ratio)")


class EnergySummary(BaseModel):
    """Aggregated statistics over a meter's available time-series consumption window."""

    meter_id: str = Field(..., description="Target meter identifier")
    reading_count: int = Field(..., description="Total readings present in window")
    oldest_reading: Optional[EnergyReading] = Field(None, description="Earliest recorded reading in window")
    latest_reading: Optional[EnergyReading] = Field(None, description="Most recent recorded reading in window")
    total_active_kwh_delta: Optional[float] = Field(
        None, description="Net kWh consumed over the window (latest kWh - earliest kWh)"
    )
    avg_voltage_r: Optional[float] = Field(None, description="Average Phase R voltage across the window")
    min_voltage_r: Optional[float] = Field(None, description="Minimum Phase R voltage recorded")
    max_voltage_r: Optional[float] = Field(None, description="Maximum Phase R voltage recorded")
    voltage_anomaly: bool = Field(
        False, description="True if any reading deviates outside nominal 210V-250V range"
    )
    readings: List[EnergyReading] = Field(default_factory=list, description="Ordered time-series interval readings")


class MeterSummary(BaseModel):
    """Summary of smart meter specification, location, and operational status."""

    meter_id: str = Field(..., description="Unique alphanumeric identifier of the meter", examples=["J100000"])
    serial_no: str = Field(..., description="Manufacturer hardware serial number", examples=["SE33962"])
    make: str = Field(..., description="Hardware manufacturer", examples=["HPL"])
    phase_type: str = Field(..., description="Electrical phase type (single or three)", examples=["single"])
    install_status: str = Field(..., description="Operational status (Installed, Faulty, Decommissioned)", examples=["Installed"])
    install_type: Optional[str] = Field(None, description="Installation category (Whole Current, CT Operated)", examples=["Whole Current"])
    build: Optional[str] = Field(None, description="Firmware or protocol build generation (legacy, v2)", examples=["legacy"])
    dt_code: str = Field(..., description="Connected Distribution Transformer identifier", examples=["DT-001"])
    geo: Optional[GeoLocation] = Field(None, description="Geographical coordinates")


class MeterDetail(MeterSummary):
    """Comprehensive meter detail including full network hierarchy and telemetry summary."""

    hierarchy: MeterHierarchy = Field(..., description="Full upstream electrical hierarchy")
    latest_reading: Optional[EnergyReading] = Field(None, description="Most recent telemetry interval if available")


class NearbyMeter(BaseModel):
    """Smart meter spatial proximity result."""

    meter: MeterSummary = Field(..., description="Meter details")
    distance_meters: float = Field(..., description="Haversine distance from search center in meters", ge=0.0)
    distance_km: float = Field(..., description="Haversine distance in kilometers", ge=0.0)
