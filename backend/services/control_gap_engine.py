
from sqlalchemy.orm import Session

from models import ControlAssessment


# Control statuses that indicate a possible security gap.
GAP_STATUSES = {
    "partially implemented",
    "not implemented",
}


def get_verified_control_gaps(
    db: Session,
    organization_id: int,
):
    """
    Identify the latest verified security-control gaps
    for an organization.

    Both organization-level and asset-level assessments
    are considered.

    An assessment is considered a confirmed gap only when:
    1. It is the latest assessment for that control and scope.
    2. Its status indicates incomplete implementation.
    3. Its evidence explicitly contains verified=True.

    Unverified or missing evidence is treated as unknown.
    """

    assessments = (
        db.query(ControlAssessment)
        .filter(
            ControlAssessment.organization_id == organization_id
        )
        .order_by(
            ControlAssessment.assessed_at.desc(),
            ControlAssessment.assessment_id.desc(),
        )
        .all()
    )

    # Keep only the latest assessment for each control
    # and scope. Scope is organization-level or asset-level.
    latest_assessments = {}

    for assessment in assessments:
        scope_key = (
            assessment.control_id,
            assessment.asset_id,
        )

        if scope_key not in latest_assessments:
            latest_assessments[scope_key] = assessment

    verified_gaps = []

    for assessment in latest_assessments.values():

        status_value = (
            assessment.status or ""
        ).strip().lower()

        if status_value not in GAP_STATUSES:
            continue

        evidence = assessment.evidence or {}

        # Explicit verification is mandatory.
        if not isinstance(evidence, dict):
            continue

        if evidence.get("verified") is not True:
            continue

        verified_gaps.append({
            "control_id": assessment.control_id,
            "asset_id": assessment.asset_id,
            "assessment_id": assessment.assessment_id,
            "status": assessment.status,
            "effectiveness_score": (
                float(assessment.effectiveness_score)
                if assessment.effectiveness_score is not None
                else None
            ),
            "verified": True,
        })

    return verified_gaps
