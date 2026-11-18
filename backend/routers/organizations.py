from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Organization
from schemas import OrganizationCreate, OrganizationResponse

router = APIRouter(
    prefix="/api/organizations",
    tags=["Organizations"]
)


@router.post(
    "/",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED
)
def create_organization(
    organization: OrganizationCreate,
    db: Session = Depends(get_db)
):
    new_organization = Organization(
        organization_name=organization.organization_name,
        industry=organization.industry,
        organization_size=organization.organization_size
    )

    db.add(new_organization)
    db.commit()
    db.refresh(new_organization)

    return new_organization


@router.get("/", response_model=list[OrganizationResponse])
def get_organizations(db: Session = Depends(get_db)):
    return db.query(Organization).order_by(
        Organization.organization_id.desc()
    ).all()


@router.get("/{organization_id}", response_model=OrganizationResponse)
def get_organization(
    organization_id: int,
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

    return organization


@router.put("/{organization_id}", response_model=OrganizationResponse)
def update_organization(
    organization_id: int,
    organization_data: OrganizationCreate,
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

    organization.organization_name = organization_data.organization_name
    organization.industry = organization_data.industry
    organization.organization_size = organization_data.organization_size

    db.commit()
    db.refresh(organization)

    return organization


@router.delete("/{organization_id}")
def delete_organization(
    organization_id: int,
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

    # Do not delete organizations that still own assets or findings.
    has_assets = db.query(Organization.organization_id).filter(
        Organization.organization_id == organization_id
    ).first()

    if has_assets:
        from models import Asset, RiskFinding, ControlAssessment, AssetMetric

        has_related_data = any([
            db.query(Asset).filter(
                Asset.organization_id == organization_id
            ).first(),
            db.query(RiskFinding).filter(
                RiskFinding.organization_id == organization_id
            ).first(),
            db.query(ControlAssessment).filter(
                ControlAssessment.organization_id == organization_id
            ).first(),
            db.query(AssetMetric).filter(
                AssetMetric.organization_id == organization_id
            ).first()
        ])

        if has_related_data:
            raise HTTPException(
                status_code=409,
                detail="Cannot delete organization with existing assets or security records."
            )

    db.delete(organization)
    db.commit()

    return {"message": "Organization deleted successfully"}
