from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import (
    SecurityInvestment,
    SecurityControl,
    InvestmentControl,
)
from schemas import (
    SecurityInvestmentCreate,
    SecurityInvestmentResponse,
)


router = APIRouter(
    prefix="/api/security-investments",
    tags=["Security Investments"]
)


# ==========================================
# HELPER: FORMAT INVESTMENT RESPONSE
# ==========================================

def format_investment_response(investment, db):
    mappings = (
        db.query(InvestmentControl)
        .filter(
            InvestmentControl.investment_id
            == investment.investment_id
        )
        .all()
    )

    return {
        "investment_id": investment.investment_id,
        "investment_name": investment.investment_name,
        "description": investment.description,
        "estimated_cost": float(investment.estimated_cost),
        "estimated_risk_reduction": (
            float(investment.estimated_risk_reduction)
            if investment.estimated_risk_reduction is not None
            else None
        ),
        "control_ids": [
            mapping.control_id for mapping in mappings
        ],
    }


# ==========================================
# CREATE INVESTMENT
# ==========================================

@router.post(
    "/",
    response_model=SecurityInvestmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_investment(
    investment_data: SecurityInvestmentCreate,
    db: Session = Depends(get_db),
):
    control_ids = investment_data.control_ids

    if any(control_id <= 0 for control_id in control_ids):
        raise HTTPException(
            status_code=400,
            detail="Control IDs must be positive integers."
        )

    if len(control_ids) != len(set(control_ids)):
        raise HTTPException(
            status_code=400,
            detail="Duplicate control IDs are not allowed."
        )

    # Verify that all supplied controls exist.
    if control_ids:
        existing_controls = (
            db.query(SecurityControl.control_id)
            .filter(
                SecurityControl.control_id.in_(control_ids)
            )
            .all()
        )

        existing_ids = {
            control.control_id for control in existing_controls
        }

        missing_ids = set(control_ids) - existing_ids

        if missing_ids:
            raise HTTPException(
                status_code=404,
                detail={
                    "message": "One or more security controls were not found.",
                    "missing_control_ids": sorted(missing_ids),
                }
            )

    investment = SecurityInvestment(
        investment_name=investment_data.investment_name,
        description=investment_data.description,
        estimated_cost=investment_data.estimated_cost,
        estimated_risk_reduction=(
            investment_data.estimated_risk_reduction
        ),
    )

    try:
        db.add(investment)
        db.flush()

        # Save investment-to-control mappings.
        for control_id in control_ids:
            mapping = InvestmentControl(
                investment_id=investment.investment_id,
                control_id=control_id,
            )
            db.add(mapping)

        db.commit()
        db.refresh(investment)

    except Exception:
        db.rollback()
        raise

    return format_investment_response(investment, db)


# ==========================================
# GET ALL INVESTMENTS
# ==========================================

@router.get(
    "/",
    response_model=list[SecurityInvestmentResponse],
)
def get_all_investments(
    db: Session = Depends(get_db),
):
    investments = (
        db.query(SecurityInvestment)
        .order_by(SecurityInvestment.investment_id.asc())
        .all()
    )

    return [
        format_investment_response(investment, db)
        for investment in investments
    ]


# ==========================================
# GET INVESTMENT BY ID
# ==========================================

@router.get(
    "/{investment_id}",
    response_model=SecurityInvestmentResponse,
)
def get_investment(
    investment_id: int,
    db: Session = Depends(get_db),
):
    investment = (
        db.query(SecurityInvestment)
        .filter(
            SecurityInvestment.investment_id == investment_id
        )
        .first()
    )

    if not investment:
        raise HTTPException(
            status_code=404,
            detail="Security investment not found."
        )

    return format_investment_response(investment, db)


# ==========================================
# DELETE INVESTMENT
# ==========================================

@router.delete("/{investment_id}")
def delete_investment(
    investment_id: int,
    db: Session = Depends(get_db),
):
    investment = (
        db.query(SecurityInvestment)
        .filter(
            SecurityInvestment.investment_id == investment_id
        )
        .first()
    )

    if not investment:
        raise HTTPException(
            status_code=404,
            detail="Security investment not found."
        )

    try:
        db.delete(investment)
        db.commit()

    except Exception:
        db.rollback()
        raise

    return {
        "message": "Security investment deleted successfully.",
        "investment_id": investment_id,
    }
