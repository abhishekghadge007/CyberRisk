from sqlalchemy.orm import Session
from sqlalchemy import func

from models import (
    Asset,
    RiskFinding,
    ControlAssessment,
    SecurityControl,
)


# Asset criticality multipliers
CRITICALITY_FACTORS = {
    "critical": 1.25,
    "high": 1.15,
    "medium": 1.00,
    "low": 0.85,
}

# Exposure multipliers
EXPOSURE_FACTORS = {
    "public": 1.20,
    "external": 1.20,
    "internet-facing": 1.20,
    "internet facing": 1.20,
    "dmz": 1.10,
    "internal": 1.00,
}

# Configurable security-control adjustments
CONTROL_RISK_ADJUSTMENTS = {
    "implemented": 0,
    "partially implemented": 5,
    "not implemented": 10,
}


def classify_risk(score: float) -> str:
    """Convert a 0–100 risk score into a risk category."""

    if score >= 70:
        return "Critical"
    if score >= 40:
        return "High"
    if score >= 20:
        return "Moderate"
    return "Low"


def calculate_control_risk(db: Session, asset: Asset) -> dict:
    """
    Calculate adjustments from verified asset-level
    security-control assessments only.
    """

    assessments = (
        db.query(ControlAssessment)
        .filter(
            ControlAssessment.asset_id == asset.asset_id
        )
        .order_by(
            ControlAssessment.assessed_at.desc(),
            ControlAssessment.assessment_id.desc()
        )
        .all()
    )

    controls = db.query(SecurityControl).all()

    control_map = {
        control.control_id: control
        for control in controls
    }

    latest_assessments = {}

    for assessment in assessments:
        if assessment.control_id not in latest_assessments:
            latest_assessments[assessment.control_id] = assessment

    evaluated_controls = []
    excluded_controls = []
    total_control_adjustment = 0.0

    for control_id, assessment in latest_assessments.items():

        control = control_map.get(control_id)

        if not control:
            excluded_controls.append({
                "control_id": control_id,
                "reason": "Security control record not found."
            })
            continue

        evidence = assessment.evidence or {}

        if evidence.get("verified") is not True:
            excluded_controls.append({
                "control_id": control_id,
                "control_key": control.control_key,
                "control_name": control.control_name,
                "status": assessment.status,
                "reason": (
                    "Assessment evidence is not verified. "
                    "No risk adjustment applied."
                )
            })
            continue

        status = (assessment.status or "").strip().lower()

        if status not in CONTROL_RISK_ADJUSTMENTS:
            excluded_controls.append({
                "control_id": control_id,
                "control_key": control.control_key,
                "control_name": control.control_name,
                "reason": "Unknown security-control status."
            })
            continue

        adjustment = CONTROL_RISK_ADJUSTMENTS[status]

        total_control_adjustment += adjustment

        evaluated_controls.append({
            "control_id": control.control_id,
            "control_key": control.control_key,
            "control_name": control.control_name,
            "status": assessment.status,
            "effectiveness_score": (
                float(assessment.effectiveness_score)
                if assessment.effectiveness_score is not None
                else None
            ),
            "verified": True,
            "risk_adjustment": adjustment,
        })

    return {
        "total_control_adjustment": round(
            total_control_adjustment, 2
        ),
        "evaluated_controls_count": len(evaluated_controls),
        "excluded_controls_count": len(excluded_controls),
        "evaluated_controls": evaluated_controls,
        "excluded_controls": excluded_controls,
        "methodology": (
            "Latest verified asset-level assessment per control. "
            "Implemented = 0, Partially Implemented = 5, "
            "Not Implemented = 10."
        )
    }


def calculate_asset_risk(db: Session, asset: Asset) -> dict:
    """
    Calculate explainable asset risk.

    Assets without open findings still receive a security-control
    analysis, but no artificial vulnerability risk score.
    """

    findings = (
        db.query(RiskFinding)
        .filter(
            RiskFinding.asset_id == asset.asset_id,
            func.lower(RiskFinding.status) == "open",
        )
        .order_by(RiskFinding.finding_id.asc())
        .all()
    )

    criticality = (asset.criticality or "medium").strip().lower()
    exposure = (asset.exposure_level or "unknown").strip().lower()

    criticality_factor = CRITICALITY_FACTORS.get(
        criticality, 1.00
    )

    exposure_factor = EXPOSURE_FACTORS.get(
        exposure, 1.00
    )

    # Always calculate security-control posture.
    control_analysis = calculate_control_risk(db, asset)

    evaluated_findings = []
    excluded_findings = []

    for finding in findings:

        if finding.likelihood is None or finding.impact is None:
            excluded_findings.append({
                "finding_id": finding.finding_id,
                "title": finding.title,
                "reason": "Likelihood or impact is missing."
            })
            continue

        likelihood = float(finding.likelihood)
        impact = float(finding.impact)

        if not (
            1 <= likelihood <= 10
            and 1 <= impact <= 10
        ):
            excluded_findings.append({
                "finding_id": finding.finding_id,
                "title": finding.title,
                "reason": (
                    "Likelihood and impact must both "
                    "be between 1 and 10."
                )
            })
            continue

        base_score = likelihood * impact

        adjusted_score = min(
            100.0,
            base_score * criticality_factor * exposure_factor
        )

        evaluated_findings.append({
            "finding_id": finding.finding_id,
            "title": finding.title,
            "category": finding.category,
            "severity": finding.severity,
            "likelihood": likelihood,
            "impact": impact,
            "base_score": round(base_score, 2),
            "adjusted_score": round(adjusted_score, 2)
        })

    # Common assessment details
    details = {
        "methodology": "CyberRisk Explainable Asset Risk Model v2",
        "asset": {
            "asset_id": asset.asset_id,
            "asset_name": asset.asset_name,
            "criticality": asset.criticality,
            "exposure_level": asset.exposure_level,
            "cloud_provider": asset.cloud_provider,
            "environment": asset.environment
        },
        "factors": {
            "criticality_factor": criticality_factor,
            "exposure_factor": exposure_factor
        },
        "open_findings_count": len(findings),
        "evaluated_findings_count": len(evaluated_findings),
        "excluded_findings": excluded_findings,
        "evaluated_findings": evaluated_findings,
        "security_control_analysis": control_analysis
    }

    # No valid vulnerability findings
    if not evaluated_findings:

        details["risk_breakdown"] = {
            "base_risk_score": None,
            "security_control_adjustment": (
                control_analysis["total_control_adjustment"]
            ),
            "final_risk_score": None,
            "reason": (
                "A vulnerability risk score cannot be calculated "
                "without valid open risk findings."
            )
        }

        return {
            "risk_score": None,
            "risk_level": "Not Assessed",
            "assessment_details": details
        }

    # Highest individual finding score
    highest_finding = max(
        evaluated_findings,
        key=lambda item: item["adjusted_score"]
    )

    base_risk_score = highest_finding["adjusted_score"]

    control_adjustment = (
        control_analysis["total_control_adjustment"]
    )

    uncapped_final_score = (
        base_risk_score + control_adjustment
    )

    risk_score = round(
        min(100.0, uncapped_final_score),
        2
    )

    risk_level = classify_risk(risk_score)

    details.update({
        "calculation": (
            "Highest Adjusted Open Finding Score "
            "+ Verified Security Control Adjustments"
        ),
        "aggregation_method": (
            "Highest adjusted open finding plus "
            "verified asset-level control adjustments"
        ),
        "highest_risk_finding_id": highest_finding["finding_id"],
        "highest_risk_finding_title": highest_finding["title"],
        "risk_breakdown": {
            "base_risk_score": base_risk_score,
            "security_control_adjustment": control_adjustment,
            "uncapped_final_score": round(
                uncapped_final_score, 2
            ),
            "final_risk_score": risk_score,
            "score_cap": 100
        },
        "score_interpretation": {
            "0-19": "Low",
            "20-39": "Moderate",
            "40-69": "High",
            "70-100": "Critical"
        }
    })

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "assessment_details": details
    }
