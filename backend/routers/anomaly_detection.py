
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Organization
from services.anomaly_detection_engine import analyze_asset_anomalies


router = APIRouter(
    prefix="/api/anomaly-detection",
    tags=["Anomaly Detection"]
)


@router.post("/organizations/{organization_id}/assets/{asset_id}/analyze")
def detect_asset_anomalies(
    organization_id: int,
    asset_id: int,
    db: Session = Depends(get_db)
):
    organization = db.query(Organization).filter(
        Organization.organization_id == organization_id
    ).first()

    if not organization:
        raise HTTPException(
            status_code=404,
            detail="Organization not found"
        )

    try:
        result = analyze_asset_anomalies(
            db=db,
            organization_id=organization_id,
            asset_id=asset_id
        )

        return result

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error)
        )

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Anomaly detection failed. Check the backend logs."
        )
