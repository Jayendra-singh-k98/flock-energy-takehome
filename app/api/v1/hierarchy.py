"""API endpoints for network topology and hierarchy traversal."""

from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies import get_hierarchy_service
from app.models.hierarchy import HierarchyTreeNode, NetworkHierarchyResponse
from app.services.hierarchy_service import HierarchyService

router = APIRouter(prefix="/hierarchy", tags=["Network Hierarchy"])


@router.get(
    "",
    response_model=NetworkHierarchyResponse,
    summary="Get complete distribution hierarchy tree",
    description=(
        "Reconstructs and returns the full 7-tier power grid hierarchy from Zones down to "
        "individual connected smart meters (Zone -> Circle -> Division -> Subdivision -> Substation -> Feeder -> DT -> Meters)."
    ),
)
def get_full_hierarchy(
    hierarchy_service: HierarchyService = Depends(get_hierarchy_service),
) -> NetworkHierarchyResponse:
    return hierarchy_service.build_network_tree()


@router.get(
    "/{level}/{code}",
    response_model=HierarchyTreeNode,
    summary="Get subtree at hierarchy node",
    description="Query a specific hierarchy entity (e.g. level='division', code='D-01') and its downstream subtree.",
)
def get_hierarchy_node(
    level: str,
    code: str,
    hierarchy_service: HierarchyService = Depends(get_hierarchy_service),
) -> HierarchyTreeNode:
    node = hierarchy_service.find_node(level=level, code=code)
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hierarchy node at level '{level}' with code '{code}' not found.",
        )
    return node
