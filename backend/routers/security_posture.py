from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Organization, SecurityControl, ControlAssessment

router = APIRouter(
    prefix="/api/security-posture",
    tags=["Security Posture"]
)


@router.get("/organizations/{organization_id}")
def get_organization_security_posture(
    organization_id: int,
    db: Session = Depends(get_db)
):

    # 1. Verify organization
    organization = db.query(Organization).filter(
        Organization.organization_id == organization_id
    ).first()

    if not organization:
        raise HTTPException(
            status_code=404,
            detail="Organization not found."
        )

    # 2. Get all available security controls
    controls = db.query(SecurityControl).order_by(
        SecurityControl.control_id
    ).all()

    # 3. Get organization-level assessments.
    # Latest assessment for each control will be used.
    assessments = db.query(ControlAssessment).filter(
        ControlAssessment.organization_id == organization_id,
        ControlAssessment.asset_id.is_(None)
    ).order_by(
        ControlAssessment.assessed_at.desc(),
        ControlAssessment.assessment_id.desc()
    ).all()

    latest_assessments = {}

    for assessment in assessments:
        if assessment.control_id not in latest_assessments:
            latest_assessments[assessment.control_id] = assessment

    # 4. Initialize counters
    implemented = 0
    partially_implemented = 0
    not_implemented = 0
    unassessed = 0

    effectiveness_scores = []
    control_details = []
    recommendations = []

    # 5. Analyze every security control
    for control in controls:

        assessment = latest_assessments.get(control.control_id)

        if assessment is None:
            unassessed += 1

            control_details.append({
                "control_id": control.control_id,
                "control_key": control.control_key,
                "control_name": control.control_name,
                "status": "Not Assessed",
                "effectiveness_score": None,
                "assessed_at": None
            })

            recommendations.append({
                "control_key": control.control_key,
                "priority": "High",
                "recommendation": (
                    f"Conduct an assessment for {control.control_name}."
                )
            })

            continue

        status_value = assessment.status

        if status_value == "Implemented":
            implemented += 1

        elif status_value == "Partially Implemented":
            partially_implemented += 1

            recommendations.append({
                "control_key": control.control_key,
                "priority": "Medium",
                "recommendation": (
                    f"Improve the implementation of {control.control_name}."
                )
            })

        elif status_value == "Not Implemented":
            not_implemented += 1

            recommendations.append({
                "control_key": control.control_key,
                "priority": "High",
                "recommendation": (
                    f"Implement {control.control_name}."
                )
            })

        if assessment.effectiveness_score is not None:
            effectiveness_scores.append(
                float(assessment.effectiveness_score)
            )

        control_details.append({
            "control_id": control.control_id,
            "control_key": control.control_key,
            "control_name": control.control_name,
            "status": status_value,
            "effectiveness_score": (
                float(assessment.effectiveness_score)
                if assessment.effectiveness_score is not None
                else None
            ),
            "assessed_at": assessment.assessed_at
        })

    # 6. Calculate percentages
    total_controls = len(controls)
    assessed_controls = total_controls - unassessed

    if total_controls > 0:
        assessment_coverage = (
            assessed_controls / total_controls
        ) * 100

        implementation_percentage = (
            implemented / total_controls
        ) * 100
    else:
        assessment_coverage = 0
        implementation_percentage = 0

    # 7. Calculate average effectiveness
    average_effectiveness = (
        sum(effectiveness_scores) / len(effectiveness_scores)
        if effectiveness_scores
        else None
    )

    # 8. Return organization security posture
    return {
        "organization_id": organization_id,

        "summary": {
            "total_controls": total_controls,
            "assessed_controls": assessed_controls,
            "unassessed_controls": unassessed,
            "implemented": implemented,
            "partially_implemented": partially_implemented,
            "not_implemented": not_implemented,
            "assessment_coverage_percentage": round(
                assessment_coverage, 2
            ),
            "implementation_percentage": round(
                implementation_percentage, 2
            ),
            "average_effectiveness_score": (
                round(average_effectiveness, 2)
                if average_effectiveness is not None
                else None
            )
        },

        "controls": control_details,

        "recommendations": recommendations,

        "methodology": (
            "Latest organization-level assessment per security control."
        ),

        "disclaimer": (
            "Results depend on recorded assessment data and are "
            "not independent verification of security controls."
        )
    }
