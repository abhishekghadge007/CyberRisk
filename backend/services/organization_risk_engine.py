from sqlalchemy.orm import Session

from models import Organization, Asset, RiskAssessment


# Criticality weights used for organization-level aggregation
CRITICALITY_WEIGHTS = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}


def classify_organization_risk(score: float) -> str:
    """Classify the organization's overall risk score."""

    if score >= 70:
        return "Critical"
    elif score >= 40:
        return "High"
    elif score >= 20:
        return "Moderate"
    else:
        return "Low"


def calculate_organization_risk(
    db: Session,
    organization_id: int
) -> dict:
    """
    Calculate organization-level risk using the latest
    numerical risk assessment for each asset.

    Uses a criticality-weighted average.

    Assets without a valid numerical risk score are
    reported separately and are not treated as zero risk.
    """

    organization = (
        db.query(Organization)
        .filter(
            Organization.organization_id == organization_id
        )
        .first()
    )

    if not organization:
        raise ValueError("Organization not found.")

    assets = (
        db.query(Asset)
        .filter(
            Asset.organization_id == organization_id
        )
        .order_by(Asset.asset_id.asc())
        .all()
    )

    total_assets = len(assets)

    if total_assets == 0:
        return {
            "organization_id": organization_id,
            "organization_name": organization.organization_name,
            "risk_score": None,
            "risk_level": "Not Assessed",
            "total_assets": 0,
            "assessed_assets": 0,
            "unassessed_assets": 0,
            "risk_distribution": {
                "Critical": 0,
                "High": 0,
                "Moderate": 0,
                "Low": 0,
            },
            "asset_risks": [],
            "highest_risk_assets": [],
            "unassessed_asset_details": [],
            "methodology": "Criticality-Weighted Average v2",
            "assessment_coverage_percentage": 0.0,
        }

    asset_risks = []
    unassessed_asset_details = []

    weighted_risk_total = 0.0
    total_weight = 0

    risk_distribution = {
        "Critical": 0,
        "High": 0,
        "Moderate": 0,
        "Low": 0,
    }

    for asset in assets:

        # Find the latest assessment for this asset.
        latest_assessment = (
            db.query(RiskAssessment)
            .filter(
                RiskAssessment.asset_id == asset.asset_id,
                RiskAssessment.organization_id == organization_id,
            )
            .order_by(
                RiskAssessment.assessed_at.desc().nullslast(),
                RiskAssessment.assessment_id.desc(),
            )
            .first()
        )

        # Determine the asset's criticality weight.
        criticality = (
            asset.criticality or "Medium"
        ).strip().lower()

        weight = CRITICALITY_WEIGHTS.get(criticality, 2)

        # Case 1: No assessment exists.
        if not latest_assessment:

            unassessed_asset_details.append({
                "asset_id": asset.asset_id,
                "asset_name": asset.asset_name,
                "criticality": asset.criticality,
                "reason": "No risk assessment available.",
            })

            continue

        # Case 2: Assessment exists, but its risk score is NULL.
        if latest_assessment.risk_score is None:

            unassessed_asset_details.append({
                "asset_id": asset.asset_id,
                "asset_name": asset.asset_name,
                "criticality": asset.criticality,
                "assessment_id": latest_assessment.assessment_id,
                "assessed_at": latest_assessment.assessed_at,
                "reason": (
                    "Latest risk assessment has no valid "
                    "numerical risk score."
                ),
            })

            continue

        # Case 3: Valid numerical risk assessment.
        risk_score = float(latest_assessment.risk_score)

        risk_level = classify_organization_risk(risk_score)

        weighted_risk_total += risk_score * weight
        total_weight += weight

        risk_distribution[risk_level] += 1

        asset_risks.append({
            "asset_id": asset.asset_id,
            "asset_name": asset.asset_name,
            "criticality": asset.criticality,
            "risk_score": round(risk_score, 2),
            "risk_level": risk_level,
            "criticality_weight": weight,
            "assessment_id": latest_assessment.assessment_id,
            "assessed_at": latest_assessment.assessed_at,
        })

    assessed_assets = len(asset_risks)
    unassessed_count = len(unassessed_asset_details)

    # Calculate the criticality-weighted organization risk.
    if total_weight > 0:

        organization_score = round(
            weighted_risk_total / total_weight,
            2
        )

        organization_level = classify_organization_risk(
            organization_score
        )

    else:
        organization_score = None
        organization_level = "Not Assessed"

    # Sort assets from highest risk to lowest risk.
    asset_risks.sort(
        key=lambda item: item["risk_score"],
        reverse=True
    )

    highest_risk_assets = asset_risks[:5]

    # Coverage includes only assets with valid numerical scores.
    coverage = round(
        (assessed_assets / total_assets) * 100,
        2
    )

    return {
        "organization_id": organization.organization_id,
        "organization_name": organization.organization_name,
        "risk_score": organization_score,
        "risk_level": organization_level,
        "total_assets": total_assets,
        "assessed_assets": assessed_assets,
        "unassessed_assets": unassessed_count,
        "risk_distribution": risk_distribution,
        "asset_risks": asset_risks,
        "highest_risk_assets": highest_risk_assets,
        "unassessed_asset_details": unassessed_asset_details,
        "methodology": "Criticality-Weighted Average v2",
        "assessment_coverage_percentage": coverage,
        "calculation": (
            "Sum of (Asset Risk Score × Criticality Weight) "
            "divided by Sum of Criticality Weights"
        ),
    }
