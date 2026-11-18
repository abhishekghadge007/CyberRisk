from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Asset, RiskAssessment
from schemas import RiskAssessmentResponse
from services.risk_engine import calculate_asset_risk


router = APIRouter(
    prefix="/api/risk-assessments",
    tags=["Risk Assessments"]
)


# ==========================================
# 1. CALCULATE AND SAVE ASSET RISK
# ==========================================

@router.post(
    "/assets/{asset_id}/calculate",
    response_model=RiskAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def calculate_and_save_asset_risk(
    asset_id: int,
    db: Session = Depends(get_db),
):
    asset = (
        db.query(Asset)
        .filter(Asset.asset_id == asset_id)
        .first()
    )

    if not asset:
        raise HTTPException(
            status_code=404,
            detail="Asset not found."
        )

    if not asset.organization_id:
        raise HTTPException(
            status_code=400,
            detail="Asset is not linked to an organization."
        )

    try:
        result = calculate_asset_risk(db, asset)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error)
        )

    assessment = RiskAssessment(
        asset_id=asset.asset_id,
        organization_id=asset.organization_id,
        risk_score=result["risk_score"],
        risk_level=result["risk_level"],
        assessment_details=result["assessment_details"],
    )

    try:
        db.add(assessment)
        db.commit()
        db.refresh(assessment)

    except Exception:
        db.rollback()
        raise

    return assessment


# ==========================================
# 2. GET LATEST ASSET RISK
# ==========================================

@router.get(
    "/assets/{asset_id}/latest",
    response_model=RiskAssessmentResponse,
)
def get_latest_asset_risk(
    asset_id: int,
    db: Session = Depends(get_db),
):
    asset = (
        db.query(Asset)
        .filter(Asset.asset_id == asset_id)
        .first()
    )

    if not asset:
        raise HTTPException(
            status_code=404,
            detail="Asset not found."
        )

    assessment = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.asset_id == asset_id)
        .order_by(RiskAssessment.assessed_at.desc())
        .first()
    )

    if not assessment:
        raise HTTPException(
            status_code=404,
            detail="No risk assessment exists for this asset yet."
        )

    return assessment


# ==========================================
# 3. GET ASSET FINANCIAL EXPOSURE
# ==========================================

@router.get("/assets/{asset_id}/financial-exposure")
def get_asset_financial_exposure(
    asset_id: int,
    db: Session = Depends(get_db),
):
    asset = (
        db.query(Asset)
        .filter(Asset.asset_id == asset_id)
        .first()
    )

    if not asset:
        raise HTTPException(
            status_code=404,
            detail="Asset not found."
        )

    if asset.estimated_asset_value is None:
        raise HTTPException(
            status_code=400,
            detail="Estimated asset value has not been provided."
        )

    assessment = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.asset_id == asset_id)
        .order_by(RiskAssessment.assessed_at.desc())
        .first()
    )

    if not assessment:
        raise HTTPException(
            status_code=404,
            detail="Calculate risk assessment before estimating financial exposure."
        )

    # Handle assets without a numerical risk score.
    if assessment.risk_score is None:
        return {
            "asset_id": asset.asset_id,
            "asset_name": asset.asset_name,
            "estimated_asset_value": float(
                asset.estimated_asset_value
            ),
            "risk_score": None,
            "risk_level": "Not Assessed",
            "estimated_financial_exposure": None,
            "currency": "INR",
            "message": (
                "Financial exposure cannot be estimated "
                "because the asset has no valid risk score."
            )
        }

    asset_value = float(asset.estimated_asset_value)
    risk_score = float(assessment.risk_score)

    estimated_exposure = asset_value * (risk_score / 100)

    return {
        "asset_id": asset.asset_id,
        "asset_name": asset.asset_name,
        "estimated_asset_value": round(asset_value, 2),
        "risk_score": round(risk_score, 2),
        "risk_level": assessment.risk_level,
        "estimated_financial_exposure": round(
            estimated_exposure, 2
        ),
        "currency": "INR",
        "calculation_method": (
            "Asset value multiplied by risk score percentage"
        )
    }


# ==========================================
# 4. GET ASSET RISK HISTORY
# ==========================================

@router.get("/assets/{asset_id}/history")
def get_asset_risk_history(
    asset_id: int,
    db: Session = Depends(get_db),
):
    asset = (
        db.query(Asset)
        .filter(Asset.asset_id == asset_id)
        .first()
    )

    if not asset:
        raise HTTPException(
            status_code=404,
            detail="Asset not found."
        )

    assessments = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.asset_id == asset_id)
        .order_by(RiskAssessment.assessed_at.asc())
        .all()
    )

    if not assessments:
        raise HTTPException(
            status_code=404,
            detail="No risk assessment history found."
        )

    history = [
        {
            "assessment_id": item.assessment_id,
            "risk_score": (
                float(item.risk_score)
                if item.risk_score is not None
                else None
            ),
            "risk_level": item.risk_level,
            "assessed_at": item.assessed_at,
        }
        for item in assessments
    ]

    # Only numerical risk scores are used for trend calculation.
    valid_scores = [
        item["risk_score"]
        for item in history
        if item["risk_score"] is not None
    ]

    if len(valid_scores) < 2:

        first_score = (
            valid_scores[0]
            if valid_scores else None
        )

        latest_score = (
            valid_scores[-1]
            if valid_scores else None
        )

        score_change = None
        trend = "Insufficient data"

    else:

        first_score = valid_scores[0]
        latest_score = valid_scores[-1]

        score_change = round(
            latest_score - first_score, 2
        )

        if score_change > 0:
            trend = "Increasing"

        elif score_change < 0:
            trend = "Decreasing"

        else:
            trend = "Stable"

    return {
        "asset_id": asset.asset_id,
        "asset_name": asset.asset_name,
        "assessment_count": len(history),
        "valid_assessment_count": len(valid_scores),
        "first_risk_score": first_score,
        "latest_risk_score": latest_score,
        "score_change": score_change,
        "risk_trend": trend,
        "history": history,
        "methodology": (
            "Historical risk score comparison using "
            "valid numerical assessments only"
        ),
        "prediction_status": (
            "Not yet enabled; more historical data is required."
        )
    }


# ==========================================
# 5. GET PREDICTIVE RISK ANALYSIS
# ==========================================

@router.get("/assets/{asset_id}/predictive-analysis")
def get_predictive_risk_analysis(
    asset_id: int,
    db: Session = Depends(get_db),
):
    # 1. Verify asset exists.
    asset = (
        db.query(Asset)
        .filter(Asset.asset_id == asset_id)
        .first()
    )

    if not asset:
        raise HTTPException(
            status_code=404,
            detail="Asset not found."
        )

    # 2. Retrieve historical assessments.
    assessments = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.asset_id == asset_id)
        .order_by(RiskAssessment.assessed_at.asc())
        .all()
    )

    if not assessments:
        raise HTTPException(
            status_code=404,
            detail="No historical risk assessments found."
        )

    latest = assessments[-1]
    latest_level = latest.risk_level

    # 3. Filter out Not Assessed records.
    valid_assessments = [
        item
        for item in assessments
        if item.risk_score is not None
    ]

    assessment_count = len(assessments)
    valid_assessment_count = len(valid_assessments)

    # 4. Handle the case where no numerical scores exist.
    if valid_assessment_count == 0:

        return {
            "asset_id": asset.asset_id,
            "asset_name": asset.asset_name,
            "latest_risk_score": None,
            "latest_risk_level": latest_level,
            "assessment_count": assessment_count,
            "valid_assessment_count": 0,
            "previous_score_change": None,
            "recent_trend": "Insufficient data",
            "risk_outlook": (
                "Risk outlook unavailable because no "
                "valid numerical risk assessments exist."
            ),
            "data_sufficiency": "Insufficient",
            "recommendations": [
                "Perform an authorized vulnerability assessment.",
                "Record and verify security findings.",
                "Review security control evidence."
            ],
            "analysis_method": (
                "Historical trend analysis and rule-based evaluation"
            ),
            "prediction_status": (
                "Prediction unavailable. No valid numerical "
                "risk scores are available."
            ),
            "disclaimer": (
                "A missing risk score does not indicate zero risk."
            )
        }

    # 5. Use the latest valid numerical assessment.
    latest_valid = valid_assessments[-1]
    latest_score = float(latest_valid.risk_score)
    latest_valid_level = latest_valid.risk_level

    if valid_assessment_count < 2:

        data_sufficiency = "Insufficient"
        outlook = "Insufficient historical data"
        score_change = None
        trend = "Unknown"

    else:

        previous = valid_assessments[-2]
        previous_score = float(previous.risk_score)

        score_change = round(
            latest_score - previous_score, 2
        )

        # 6. Detect recent risk trends.
        if score_change >= 5:

            trend = "Increasing"
            outlook = "Potential deterioration"

        elif score_change <= -5:

            trend = "Decreasing"
            outlook = "Improving"

        else:

            trend = "Stable"
            outlook = "Stable risk conditions"

        if valid_assessment_count < 5:
            data_sufficiency = "Low"

        elif valid_assessment_count < 10:
            data_sufficiency = "Moderate"

        else:
            data_sufficiency = "Better historical coverage"

    # 7. Generate preventive recommendations.
    recommendations = []

    normalized_level = str(
        latest_valid_level
    ).lower()

    if normalized_level == "critical":

        recommendations.extend([
            "Immediately investigate critical vulnerabilities.",
            "Review firewall and network security configurations.",
            "Verify MFA protection for privileged accounts.",
            "Prioritize immediate security remediation."
        ])

    elif normalized_level == "high":

        recommendations.extend([
            "Prioritize high-severity vulnerabilities.",
            "Review access permissions and security controls.",
            "Strengthen endpoint and network protection."
        ])

    elif normalized_level in ("moderate", "medium"):

        recommendations.extend([
            "Schedule regular vulnerability assessments.",
            "Review security configurations.",
            "Monitor changes in asset risk scores."
        ])

    else:

        recommendations.extend([
            "Maintain existing security controls.",
            "Continue periodic vulnerability assessments.",
            "Monitor asset health and security posture."
        ])

    # 8. Add recommendations based on risk movement.
    if score_change is not None:

        if score_change >= 5:

            recommendations.append(
                "Investigate the recent increase in risk score."
            )

        elif score_change <= -5:

            recommendations.append(
                "Continue current remediation activities "
                "to maintain the improvement."
            )

    # 9. Return predictive analysis.
    return {
        "asset_id": asset.asset_id,
        "asset_name": asset.asset_name,

        "latest_risk_score": round(latest_score, 2),
        "latest_risk_level": latest_valid_level,

        "assessment_count": assessment_count,
        "valid_assessment_count": valid_assessment_count,

        "previous_score_change": score_change,
        "recent_trend": trend,

        "risk_outlook": outlook,

        "data_sufficiency": data_sufficiency,

        "recommendations": recommendations,

        "analysis_method": (
            "Historical trend analysis and rule-based risk evaluation"
        ),

        "prediction_status": (
            "Rule-based analysis only. "
            "Machine learning forecasting is not enabled."
        ),

        "disclaimer": (
            "Risk outlook is an indicator based on historical "
            "assessments, not a guaranteed future prediction."
        )
    }
