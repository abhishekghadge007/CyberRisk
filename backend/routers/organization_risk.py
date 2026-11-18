from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Organization
from schemas import OrganizationRiskSummaryResponse

from services.organization_risk_engine import (
    calculate_organization_risk
)


router = APIRouter(
    prefix="/api/organizations",
    tags=["Organization Risk"]
)


@router.get(
    "/{organization_id}/risk-summary",
    response_model=OrganizationRiskSummaryResponse,
)
def get_organization_risk_summary(
    organization_id: int,
    db: Session = Depends(get_db),
):

    organization = (
        db.query(Organization)
        .filter(
            Organization.organization_id == organization_id
        )
        .first()
    )

    if not organization:
        raise HTTPException(
            status_code=404,
            detail="Organization not found."
        )

    try:
        result = calculate_organization_risk(
            db,
            organization_id
        )

        return result

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error)
        )

    
@router.get("/{organization_id}/predictive-analysis")
def get_organization_predictive_analysis(
    organization_id: int,
    db: Session = Depends(get_db),
):
    from services.organization_predictive_engine import (
        analyze_organization_history
    )

    try:
        result = analyze_organization_history(
            db,
            organization_id
        )

        return result

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error)
        )
