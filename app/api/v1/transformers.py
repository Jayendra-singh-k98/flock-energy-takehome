"""API endpoints for Distribution Transformers (DTs)."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_transformer_service
from app.models.transformer import DistributionTransformer, TransformerDetail
from app.services.transformer_service import TransformerService

router = APIRouter(prefix="/transformers", tags=["Distribution Transformers"])


@router.get(
    "",
    response_model=List[DistributionTransformer],
    summary="List distribution transformers",
    description="Retrieve distribution transformers along with aggregated connected meter asset counts and rated capacity.",
)
def list_transformers(
    feeder_code: Optional[str] = Query(
        None, description="Filter transformers by Feeder code (e.g. F-001)"
    ),
    transformer_service: TransformerService = Depends(get_transformer_service),
) -> List[DistributionTransformer]:
    return transformer_service.list_transformers(feeder_code=feeder_code)


@router.get(
    "/{code}",
    response_model=TransformerDetail,
    summary="Get transformer detail",
    description="Retrieve a specific transformer installation along with the complete roster of connected smart meters.",
)
def get_transformer(
    code: str,
    transformer_service: TransformerService = Depends(get_transformer_service),
) -> TransformerDetail:
    transformer = transformer_service.get_transformer_detail(code)
    if not transformer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Distribution Transformer with code '{code}' not found.",
        )
    return transformer
