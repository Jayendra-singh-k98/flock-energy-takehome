"""Data models for Distribution Transformers (DTs)."""

from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.meter import MeterSummary


class DistributionTransformer(BaseModel):
    """Distribution Transformer specification and connected asset metrics."""

    code: str = Field(..., description="Unique DT code", examples=["DT-001"])
    name: str = Field(..., description="Name of the transformer installation", examples=["Malviya Nagar DT 1"])
    feeder_code: str = Field(..., description="Feeder code supplying this DT", examples=["F-001"])
    capacity_kva: float = Field(..., description="Rated capacity in kVA", examples=[100.0])
    connected_meters_count: int = Field(0, description="Total smart meters fed by this transformer", ge=0)
    installed_meters_count: int = Field(0, description="Active installed meters under this transformer", ge=0)
    faulty_meters_count: int = Field(0, description="Faulty meters under this transformer", ge=0)
    decommissioned_meters_count: int = Field(0, description="Decommissioned meters under this transformer", ge=0)


class TransformerDetail(DistributionTransformer):
    """Distribution Transformer with complete list of connected meter summaries."""

    connected_meters: List[MeterSummary] = Field(
        default_factory=list, description="All smart meters linked to this transformer"
    )
