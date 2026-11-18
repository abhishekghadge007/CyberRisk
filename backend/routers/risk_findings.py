from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import RiskFinding, Organization, Asset
from schemas import RiskFindingCreate, RiskFindingResponse
from services.recommendation_engine import (generate_organization_recommendations,)

router = APIRouter(
    prefix="/api/risk-findings",
    tags=["Risk Findings"]
)


# CREATE A RISK FINDING
@router.post(
    "/",
    response_model=RiskFindingResponse,
    status_code=status.HTTP_201_CREATED
)
def create_risk_finding(
    finding: RiskFindingCreate,
    db: Session = Depends(get_db)
):
    # Check whether organization exists
    organization = db.query(Organization).filter(
        Organization.organization_id == finding.organization_id
    ).first()

    if not organization:
        raise HTTPException(
            status_code=404,
            detail="Organization not found"
        )

    # If asset_id is provided, check whether asset exists
    if finding.asset_id is not None:
        asset = db.query(Asset).filter(
            Asset.asset_id == finding.asset_id,
            Asset.organization_id == finding.organization_id
        ).first()

        if not asset:
            raise HTTPException(
                status_code=404,
                detail="Asset not found in the specified organization"
            )

    new_finding = RiskFinding(
        organization_id=finding.organization_id,
        asset_id=finding.asset_id,
        category=finding.category,
        source=finding.source,
        title=finding.title,
        description=finding.description,
        severity=finding.severity,
        likelihood=finding.likelihood,
        impact=finding.impact,
        evidence=finding.evidence
    )

    db.add(new_finding)
    db.commit()
    db.refresh(new_finding)

    return new_finding


# GET ALL RISK FINDINGS
@router.get("/", response_model=list[RiskFindingResponse])
def get_risk_findings(
    organization_id: int | None = None,
    asset_id: int | None = None,
    finding_status: str | None = None,
    db: Session = Depends(get_db)
):
    query = db.query(RiskFinding)

    if organization_id is not None:
        query = query.filter(
            RiskFinding.organization_id == organization_id
        )

    if asset_id is not None:
        query = query.filter(
            RiskFinding.asset_id == asset_id
        )

    if finding_status is not None:
        query = query.filter(
            RiskFinding.status == finding_status
        )

    return query.order_by(
        RiskFinding.detected_at.desc()
    ).all()


# GET A PARTICULAR RISK FINDING
@router.get("/{finding_id}", response_model=RiskFindingResponse)
def get_risk_finding(
    finding_id: int,
    db: Session = Depends(get_db)
):
    finding = db.query(RiskFinding).filter(
        RiskFinding.finding_id == finding_id
    ).first()

    if not finding:
        raise HTTPException(
            status_code=404,
            detail="Risk finding not found"
        )

    return finding


# UPDATE A RISK FINDING
@router.put("/{finding_id}", response_model=RiskFindingResponse)
def update_risk_finding(
    finding_id: int,
    finding_data: RiskFindingCreate,
    db: Session = Depends(get_db)
):
    finding = db.query(RiskFinding).filter(
        RiskFinding.finding_id == finding_id
    ).first()

    if not finding:
        raise HTTPException(
            status_code=404,
            detail="Risk finding not found"
        )

    organization = db.query(Organization).filter(
        Organization.organization_id == finding_data.organization_id
    ).first()

    if not organization:
        raise HTTPException(
            status_code=404,
            detail="Organization not found"
        )

    if finding_data.asset_id is not None:
        asset = db.query(Asset).filter(
            Asset.asset_id == finding_data.asset_id,
            Asset.organization_id == finding_data.organization_id
        ).first()

        if not asset:
            raise HTTPException(
                status_code=404,
                detail="Asset not found in the specified organization"
            )

    finding.organization_id = finding_data.organization_id
    finding.asset_id = finding_data.asset_id
    finding.category = finding_data.category
    finding.source = finding_data.source
    finding.title = finding_data.title
    finding.description = finding_data.description
    finding.severity = finding_data.severity
    finding.likelihood = finding_data.likelihood
    finding.impact = finding_data.impact
    finding.evidence = finding_data.evidence
    finding.last_seen = datetime.now(timezone.utc)

    db.commit()
    db.refresh(finding)

    return finding


# DELETE A RISK FINDING
@router.delete("/{finding_id}")
def delete_risk_finding(
    finding_id: int,
    db: Session = Depends(get_db)
):
    finding = db.query(RiskFinding).filter(
        RiskFinding.finding_id == finding_id
    ).first()

    if not finding:
        raise HTTPException(
            status_code=404,
            detail="Risk finding not found"
        )

    db.delete(finding)
    db.commit()

    return {
        "message": "Risk finding deleted successfully",
        "finding_id": finding_id
    }


# ==========================================
# AI-DRIVEN SECURITY RECOMMENDATIONS
# ==========================================

@router.get("/recommendations/{organization_id}")
def get_security_recommendations(
    organization_id: int,
    db: Session = Depends(get_db)
):

    organization = db.query(Organization).filter(
        Organization.organization_id == organization_id
    ).first()

    if not organization:
        raise HTTPException(
            status_code=404,
            detail="Organization not found."
        )

    findings = db.query(RiskFinding).filter(
        RiskFinding.organization_id == organization_id,
        RiskFinding.status.ilike("open")
    ).all()

    result = generate_organization_recommendations(findings)

    return {
        "organization_id": organization_id,
        "organization_name": organization.organization_name,
        **result
    }