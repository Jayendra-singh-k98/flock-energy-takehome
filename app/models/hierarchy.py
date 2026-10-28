"""Data models for reconstructing and traversing the electrical network hierarchy."""

from typing import List, Optional
from pydantic import BaseModel, Field


class HierarchyTreeNode(BaseModel):
    """Recursive tree node representing a tier in the power distribution network."""

    id: str = Field(..., description="Unique node identifier or code", examples=["Z-01"])
    code: str = Field(..., description="Entity code", examples=["Z-01"])
    name: str = Field(..., description="Display name of the entity", examples=["Jaipur Zone 1"])
    level: str = Field(
        ...,
        description="Hierarchy tier (zone, circle, division, subdivision, substation, feeder, dt)",
        examples=["zone"],
    )
    meter_count: int = Field(0, description="Total meters connected downstream of this node", ge=0)
    children: List["HierarchyTreeNode"] = Field(
        default_factory=list, description="Child nodes downstream in the hierarchy"
    )
    meter_ids: Optional[List[str]] = Field(
        None, description="Directly connected meter IDs (populated at DT level)"
    )


class NetworkHierarchyResponse(BaseModel):
    """Top-level hierarchy response representing the complete utility distribution grid."""

    root_zones: List[HierarchyTreeNode] = Field(..., description="List of administrative zones")
    total_zones: int = Field(..., description="Number of zones")
    total_substations: int = Field(..., description="Total substations in network")
    total_feeders: int = Field(..., description="Total feeders in network")
    total_transformers: int = Field(..., description="Total distribution transformers")
    total_meters: int = Field(..., description="Total smart meters indexed")
