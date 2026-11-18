from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models import Asset, AssetMetric
from schemas import AssetMetricCreate, AssetMetricResponse


router = APIRouter(
    prefix="/api/asset-metrics",
    tags=["Asset Metrics"]
)


# ==========================================
# 1. COLLECT ASSET METRICS
# ==========================================

@router.post(
    "/",
    response_model=AssetMetricResponse,
    status_code=status.HTTP_201_CREATED
)
def create_asset_metric(
    metric_data: AssetMetricCreate,
    db: Session = Depends(get_db)
):
    # Verify that the asset belongs to the supplied organization.
    asset = db.query(Asset).filter(
        Asset.asset_id == metric_data.asset_id,
        Asset.organization_id == metric_data.organization_id
    ).first()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found in the specified organization"
        )

    # Do not save completely empty metric records.
    metric_values = [
        metric_data.cpu_usage,
        metric_data.memory_usage,
        metric_data.disk_usage,
        metric_data.network_in,
        metric_data.network_out
    ]

    if all(value is None for value in metric_values) and not metric_data.additional_metrics:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one metric value must be provided"
        )

    new_metric = AssetMetric(**metric_data.model_dump())

    db.add(new_metric)
    db.commit()
    db.refresh(new_metric)

    return new_metric


# ==========================================
# 2. GET ORGANIZATION METRICS
# ==========================================

@router.get(
    "/",
    response_model=list[AssetMetricResponse]
)
def get_asset_metrics(
    organization_id: int,
    asset_id: int | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    query = db.query(AssetMetric).filter(
        AssetMetric.organization_id == organization_id
    )

    if asset_id is not None:
        query = query.filter(
            AssetMetric.asset_id == asset_id
        )

    return query.order_by(
        AssetMetric.observed_at.desc()
    ).limit(limit).all()


# ==========================================
# 3. GET LATEST METRICS FOR AN ASSET
# ==========================================

@router.get(
    "/assets/{asset_id}/latest",
    response_model=AssetMetricResponse
)
def get_latest_asset_metric(
    asset_id: int,
    organization_id: int,
    db: Session = Depends(get_db)
):
    asset = db.query(Asset).filter(
        Asset.asset_id == asset_id,
        Asset.organization_id == organization_id
    ).first()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found in the specified organization"
        )

    metric = db.query(AssetMetric).filter(
        AssetMetric.asset_id == asset_id,
        AssetMetric.organization_id == organization_id
    ).order_by(
        AssetMetric.observed_at.desc()
    ).first()

    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No metrics have been collected for this asset"
        )

    return metric
