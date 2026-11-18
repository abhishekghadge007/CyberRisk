
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel

from database import get_db
from models import Asset, Organization, ScanJob, ScanResult
from schemas import (
    AssetCreate,
    AssetResponse,
    DeviceScanHistoryItem
)

router = APIRouter(
    prefix="/api/assets",
    tags=["Assets"]
)


# ==========================================
# ASSET TRANSFER REQUEST
# ==========================================

class AssetTransferRequest(BaseModel):
    organization_id: int


# ==========================================
# CREATE ASSET
# ==========================================

@router.post("/", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
def create_asset(
    asset_data: AssetCreate,
    db: Session = Depends(get_db)
):
    organization = db.query(Organization).filter(
        Organization.organization_id == asset_data.organization_id
    ).first()

    if not organization:
        raise HTTPException(
            status_code=404,
            detail="Organization not found"
        )

    new_asset = Asset(**asset_data.model_dump())

    db.add(new_asset)
    db.commit()
    db.refresh(new_asset)

    return new_asset


# ==========================================
# GLOBAL ASSET INVENTORY
# ==========================================

@router.get("/global", response_model=list[AssetResponse])
def get_global_assets(
    organization_id: int = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    if limit < 1 or limit > 500:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 500"
        )

    if offset < 0:
        raise HTTPException(
            status_code=400,
            detail="Offset cannot be negative"
        )

    query = db.query(Asset)

    if organization_id is not None:
        query = query.filter(
            Asset.organization_id == organization_id
        )

    return query.order_by(
        Asset.last_seen.desc()
    ).offset(offset).limit(limit).all()


# ==========================================
# ORGANIZATION ASSETS
# ==========================================

@router.get("/", response_model=list[AssetResponse])
def get_assets(
    organization_id: int,
    db: Session = Depends(get_db)
):
    return db.query(Asset).filter(
        Asset.organization_id == organization_id
    ).all()


# ==========================================
# TRANSFER ASSET TO ANOTHER ORGANIZATION
# ==========================================

@router.post("/{asset_id}/transfer", response_model=AssetResponse)
def transfer_asset(
    asset_id: int,
    transfer_data: AssetTransferRequest,
    db: Session = Depends(get_db)
):
    asset = db.query(Asset).filter(
        Asset.asset_id == asset_id
    ).first()

    if not asset:
        raise HTTPException(
            status_code=404,
            detail="Asset not found"
        )

    new_organization = db.query(Organization).filter(
        Organization.organization_id == transfer_data.organization_id
    ).first()

    if not new_organization:
        raise HTTPException(
            status_code=404,
            detail="Target organization not found"
        )

    if asset.organization_id == transfer_data.organization_id:
        raise HTTPException(
            status_code=400,
            detail="Asset already belongs to this organization"
        )

    # Prevent duplicate IP addresses in the target organization.
    duplicate_asset = db.query(Asset).filter(
        Asset.organization_id == transfer_data.organization_id,
        func.host(Asset.ip_address) == str(asset.ip_address)
    ).first()

    if duplicate_asset:
        raise HTTPException(
            status_code=409,
            detail=(
                "An asset with this IP address already exists "
                "in the target organization."
            )
        )

    old_organization_id = asset.organization_id

    try:
        asset.organization_id = transfer_data.organization_id

        db.commit()
        db.refresh(asset)

        return asset

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Asset transfer failed. No changes were committed."
        )


# ==========================================
# DEVICE SCAN HISTORY
# ==========================================

@router.get(
    "/{asset_id}/scan-history",
    response_model=list[DeviceScanHistoryItem]
)
def get_asset_scan_history(
    asset_id: int,
    db: Session = Depends(get_db)
):
    asset = db.query(Asset).filter(
        Asset.asset_id == asset_id
    ).first()

    if not asset:
        raise HTTPException(
            status_code=404,
            detail="Asset not found"
        )

    history = db.query(
        ScanJob,
        func.count(ScanResult.result_id).label("result_count")
    ).join(
        ScanResult,
        ScanResult.scan_id == ScanJob.scan_id
    ).filter(
        ScanResult.asset_id == asset_id
    ).group_by(
        ScanJob.scan_id
    ).order_by(
        ScanJob.created_at.desc()
    ).all()

    return [
        {
            "scan_id": scan.scan_id,
            "organization_id": scan.organization_id,
            "target_network": scan.target_network,
            "status": scan.status,
            "started_at": scan.started_at,
            "completed_at": scan.completed_at,
            "created_at": scan.created_at,
            "result_count": result_count
        }
        for scan, result_count in history
    ]


# ==========================================
# GET SINGLE ASSET
# ==========================================

@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset(
    asset_id: int,
    db: Session = Depends(get_db)
):
    asset = db.query(Asset).filter(
        Asset.asset_id == asset_id
    ).first()

    if not asset:
        raise HTTPException(
            status_code=404,
            detail="Asset not found"
        )

    return asset


# ==========================================
# DELETE ASSET
# ==========================================

@router.delete("/{asset_id}")
def delete_asset(
    asset_id: int,
    db: Session = Depends(get_db)
):
    asset = db.query(Asset).filter(
        Asset.asset_id == asset_id
    ).first()

    if not asset:
        raise HTTPException(
            status_code=404,
            detail="Asset not found"
        )

    db.delete(asset)
    db.commit()

    return {"message": "Asset deleted successfully"}
