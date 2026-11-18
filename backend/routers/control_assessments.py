from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Organization,
    Asset,
    SecurityControl,
    ControlAssessment
)
from schemas import (
    ControlAssessmentCreate,
    ControlAssessmentResponse
)

router = APIRouter(
    prefix="/api/control-assessments",
    tags=["Control Assessments"]
)


VALID_STATUSES = {
    "Implemented",
    "Partially Implemented",
    "Not Implemented"
}


# CREATE A CONTROL ASSESSMENT
@router.post(
    "/",
    response_model=ControlAssessmentResponse,
    status_code=status.HTTP_201_CREATED
)
def create_control_assessment(
    assessment: ControlAssessmentCreate,
    db: Session = Depends(get_db)
):

    # Check organization
    organization = db.query(Organization).filter(
        Organization.organization_id == assessment.organization_id
    ).first()

    if not organization:
        raise HTTPException(
            status_code=404,
            detail="Organization not found."
        )

    # Check security control
    control = db.query(SecurityControl).filter(
        SecurityControl.control_id == assessment.control_id
    ).first()

    if not control:
        raise HTTPException(
            status_code=404,
            detail="Security control not found."
        )

    # Check asset, if supplied
    if assessment.asset_id is not None:

        asset = db.query(Asset).filter(
            Asset.asset_id == assessment.asset_id,
            Asset.organization_id == assessment.organization_id
        ).first()

        if not asset:
            raise HTTPException(
                status_code=404,
                detail="Asset not found in this organization."
            )

    # Validate implementation status
    if assessment.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid status. Use Implemented, "
                "Partially Implemented, or Not Implemented."
            )
        )

    # Validate effectiveness score
    if assessment.effectiveness_score is not None:
        if not 0 <= assessment.effectiveness_score <= 100:
            raise HTTPException(
                status_code=400,
                detail="Effectiveness score must be between 0 and 100."
            )

    new_assessment = ControlAssessment(
        organization_id=assessment.organization_id,
        asset_id=assessment.asset_id,
        control_id=assessment.control_id,
        status=assessment.status,
        effectiveness_score=assessment.effectiveness_score,
        evidence=assessment.evidence,
        next_review_at=assessment.next_review_at
    )

    db.add(new_assessment)
    db.commit()
    db.refresh(new_assessment)

    return new_assessment


# GET CONTROL ASSESSMENTS
@router.get(
    "/",
    response_model=list[ControlAssessmentResponse]
)
def get_control_assessments(
    organization_id: int = None,
    asset_id: int = None,
    db: Session = Depends(get_db)
):

    query = db.query(ControlAssessment)

    if organization_id is not None:
        query = query.filter(
            ControlAssessment.organization_id == organization_id
        )

    if asset_id is not None:
        query = query.filter(
            ControlAssessment.asset_id == asset_id
        )

    return query.order_by(
        ControlAssessment.assessment_id.desc()
    ).all()


# GET CONTROL ASSESSMENT BY ID
@router.get(
    "/{assessment_id}",
    response_model=ControlAssessmentResponse
)
def get_control_assessment(
    assessment_id: int,
    db: Session = Depends(get_db)
):

    assessment = db.query(ControlAssessment).filter(
        ControlAssessment.assessment_id == assessment_id
    ).first()

    if not assessment:
        raise HTTPException(
            status_code=404,
            detail="Control assessment not found."
        )

    return assessment
