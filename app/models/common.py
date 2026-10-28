"""Common schema and pagination models."""

import math
from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationMeta(BaseModel):
    """Metadata regarding pagination state."""

    page: int = Field(..., description="Current page number (1-indexed)", ge=1)
    page_size: int = Field(..., description="Number of items per page", ge=1)
    total_items: int = Field(..., description="Total count of items matching the query", ge=0)
    total_pages: int = Field(..., description="Total available pages", ge=0)
    has_next: bool = Field(..., description="True if next page exists")
    has_prev: bool = Field(..., description="True if previous page exists")

    @classmethod
    def create(cls, page: int, page_size: int, total_items: int) -> "PaginationMeta":
        """Factory method to calculate pagination boundaries."""
        total_pages = math.ceil(total_items / page_size) if page_size > 0 else 0
        return cls(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard generic wrapper for paginated collections."""

    data: List[T] = Field(..., description="List of items for current page")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")


class HealthStatus(BaseModel):
    """System health check and upstream synchronization status."""

    status: str = Field("healthy", description="Overall health state")
    portal_connected: bool = Field(..., description="Whether upstream portal is reachable")
    indexed_meters: int = Field(..., description="Number of meters currently indexed in memory")
    indexed_transformers: int = Field(..., description="Number of transformers indexed in memory")
    cache_age_seconds: Optional[float] = Field(
        None, description="Seconds since last full index synchronization"
    )
    cache_ttl_seconds: int = Field(..., description="Cache expiration policy")
