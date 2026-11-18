from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Asset, SecurityControl, ControlAssessment


router = APIRouter(
    prefix="/api/security-posture",
    tags=["Asset Security Posture"]
)


@router.get("/assets/{asset_id}")
def get_asset_security_posture(
    asset_id: int,
    db: Session = Depends(get_db)
):
    """
    Get the security posture of an individual asset.

    Only assessments linked to this specific asset are considered.
    Organization-level assessments are not included.
    """

    # 1. Verify that the asset exists
    asset = db.query(Asset).filter(
        Asset.asset_id == asset_id
    ).first()

    if not asset:
        raise HTTPException(
            status_code=404,
            detail="Asset not found."
        )

    # 2. Fetch all available security controls
    controls = db.query(SecurityControl).order_by(
        SecurityControl.control_id
    ).all()

    # 3. Fetch assessments belonging only to this asset
    assessments = db.query(ControlAssessment).filter(
        ControlAssessment.asset_id == asset_id
    ).order_by(
        ControlAssessment.assessed_at.desc(),
        ControlAssessment.assessment_id.desc()
    ).all()

    # 4. Keep only the latest assessment for each control
    latest_assessments = {}

    for assessment in assessments:
        if assessment.control_id not in latest_assessments:
            latest_assessments[assessment.control_id] = assessment

    # 5. Initialize summary counters
    total_controls = len(controls)
    implemented = 0
    partially_implemented = 0
    not_implemented = 0
    unassessed = 0

    effectiveness_scores = []
    control_results = []
    recommendations = []

    # 6. Evaluate every security control
    for control in controls:

        assessment = latest_assessments.get(
            control.control_id
        )

        if assessment is None:
            status = "Unassessed"
            effectiveness_score = None
            assessed_at = None
            evidence = None

            unassessed += 1

            recommendations.append({
                "control_key": control.control_key,
                "priority": "High",
                "recommendation": (
                    f"Assess {control.control_name} "
                    "for this asset."
                )
            })

        else:
            status = assessment.status
            effectiveness_score = (
                float(assessment.effectiveness_score)
                if assessment.effectiveness_score is not None
                else None
            )

            assessed_at = assessment.assessed_at
            evidence = assessment.evidence

            if status == "Implemented":
                implemented += 1

            elif status == "Partially Implemented":
                partially_implemented += 1

                recommendations.append({
                    "control_key": control.control_key,
                    "priority": "Medium",
                    "recommendation": (
                        f"Improve {control.control_name} "
                        "implementation on this asset."
                    )
                })

            elif status == "Not Implemented":
                not_implemented += 1

                recommendations.append({
                    "control_key": control.control_key,
                    "priority": "High",
                    "recommendation": (
                        f"Implement {control.control_name} "
                        "on this asset."
                    )
                })

            if effectiveness_score is not None:
                effectiveness_scores.append(
                    effectiveness_score
                )

        control_results.append({
            "control_id": control.control_id,
            "control_key": control.control_key,
            "control_name": control.control_name,
            "category": control.category,
            "status": status,
            "effectiveness_score": effectiveness_score,
            "assessed_at": assessed_at,
            "evidence": evidence
        })

    # 7. Calculate assessment coverage
    assessed_controls = total_controls - unassessed

    coverage_percentage = (
        round((assessed_controls / total_controls) * 100, 2)
        if total_controls > 0
        else 0
    )

    # 8. Calculate implementation percentage
    implementation_percentage = (
        round((implemented / total_controls) * 100, 2)
        if total_controls > 0
        else 0
    )

    # 9. Calculate average effectiveness
    average_effectiveness = (
        round(
            sum(effectiveness_scores) /
            len(effectiveness_scores),
            2
        )
        if effectiveness_scores
        else None
    )

    # 10. Return asset security posture
    return {
        "asset_id": asset.asset_id,
        "asset_name": asset.asset_name,
        "organization_id": asset.organization_id,

        "summary": {
            "total_controls": total_controls,
            "assessed_controls": assessed_controls,
            "unassessed_controls": unassessed,
            "implemented": implemented,
            "partially_implemented": partially_implemented,
            "not_implemented": not_implemented,
            "assessment_coverage_percentage": coverage_percentage,
            "implementation_percentage": implementation_percentage,
            "average_effectiveness_score": average_effectiveness
        },

        "controls": control_results,

        "recommendations": recommendations,

        "methodology": (
            "Latest assessment per security control "
            "for the selected asset only."
        ),

        "disclaimer": (
            "Results depend on recorded assessment data "
            "and do not independently verify security controls."
        )
    }
