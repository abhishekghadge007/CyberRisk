
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import func

from models import (
    Organization,
    Asset,
    RiskAssessment,
    RiskFinding,
    AssetMetric,
)

from services.organization_risk_engine import (
    calculate_organization_risk,
    CRITICALITY_WEIGHTS,
    classify_organization_risk,
)


def get_metric_summary(db: Session, organization_id: int):
    rows = (
        db.query(
            AssetMetric.asset_id,
            func.count(AssetMetric.metric_id).label("observation_count"),
            func.max(AssetMetric.observed_at).label("latest_observed_at"),
        )
        .filter(
            AssetMetric.organization_id == organization_id
        )
        .group_by(AssetMetric.asset_id)
        .all()
    )

    return {
        row.asset_id: {
            "observation_count": int(row.observation_count),
            "latest_observed_at": row.latest_observed_at,
        }
        for row in rows
    }


def get_current_risk_posture(risk_level):
    """
    Current posture comes from the existing organization risk engine.
    It is separate from historical risk movement.
    """

    level = (risk_level or "").strip().lower()

    if level == "critical":
        return "Critical"

    if level == "high":
        return "High"

    if level == "moderate":
        return "Moderate"

    if level == "low":
        return "Low"

    return "Not Assessed"


def get_emerging_risk_status(severity_distribution, anomaly_count):
    """
    Emerging risk status is based on currently open findings
    and operational anomalies, not historical score movement.
    """

    if severity_distribution["Critical"] > 0:
        return "Critical warnings"

    if severity_distribution["High"] > 0:
        return "High warnings"

    if anomaly_count > 0:
        return "Operational warnings"

    if severity_distribution["Medium"] > 0:
        return "Moderate warnings"

    if severity_distribution["Low"] > 0:
        return "Low warnings"

    return "No open warnings"


def analyze_organization_history(
    db: Session,
    organization_id: int
) -> dict:
    """
    Integrated organization risk analysis.

    Combines:
    1. Historical numerical risk assessments.
    2. Open security findings.
    3. Statistical operational anomalies.
    4. Available asset telemetry.

    Historical trend, current risk posture and emerging risk
    status are reported separately.

    This is an explainable rule-based analysis.
    It does not claim to be trained ML forecasting.
    """

    # 1. Verify organization

    organization = (
        db.query(Organization)
        .filter(
            Organization.organization_id == organization_id
        )
        .first()
    )

    if not organization:
        raise ValueError("Organization not found.")

    # 2. Retrieve organization assets

    assets = (
        db.query(Asset)
        .filter(
            Asset.organization_id == organization_id
        )
        .order_by(Asset.asset_id.asc())
        .all()
    )

    if not assets:
        return {
            "organization_id": organization_id,
            "organization_name": organization.organization_name,
            "organization_risk_score": None,
            "organization_risk_level": "Not Assessed",
            "organization_outlook": "Insufficient data",
            "organization_historical_trend": "Insufficient data",
            "current_risk_posture": "Not Assessed",
            "emerging_risk_status": "No open warnings",
            "organization_risk_score_change": None,
            "total_assets": 0,
            "assets_with_history": 0,
            "assets_without_history": 0,
            "assets_with_multiple_assessments": 0,
            "total_historical_assessments": 0,
            "valid_historical_assessments": 0,
            "unassessed_assessments": 0,
            "risk_distribution": {
                "Critical": 0,
                "High": 0,
                "Moderate": 0,
                "Low": 0,
            },
            "trend_distribution": {
                "Increasing": 0,
                "Decreasing": 0,
                "Stable": 0,
                "Insufficient data": 0,
            },
            "open_findings": 0,
            "open_operational_anomalies": 0,
            "finding_severity_distribution": {
                "Critical": 0,
                "High": 0,
                "Medium": 0,
                "Low": 0,
            },
            "telemetry_summary": {
                "assets_with_telemetry": 0,
                "assets_without_telemetry": 0,
                "total_observations": 0,
            },
            "data_sufficiency": "Insufficient",
            "asset_analysis": [],
            "emerging_risk_signals": [],
            "recommendations": [
                "Register assets and perform initial risk assessments."
            ],
            "analysis_method": "Historical and operational risk signal analysis",
            "prediction_status": (
                "Rule-based risk outlook only. "
                "Machine learning forecasting is not enabled."
            ),
            "disclaimer": (
                "Historical trends, current risk posture and emerging "
                "risk signals are separate indicators. This analysis "
                "does not guarantee future incident predictions."
            ),
        }

    asset_ids = [asset.asset_id for asset in assets]

    # 3. Retrieve historical assessments

    assessments = (
        db.query(RiskAssessment)
        .filter(
            RiskAssessment.organization_id == organization_id,
            RiskAssessment.asset_id.in_(asset_ids),
        )
        .order_by(
            RiskAssessment.asset_id.asc(),
            RiskAssessment.assessed_at.asc().nullslast(),
            RiskAssessment.assessment_id.asc(),
        )
        .all()
    )

    history_by_asset = {}

    for assessment in assessments:
        history_by_asset.setdefault(
            assessment.asset_id, []
        ).append(assessment)

    # 4. Retrieve open findings

    open_findings = (
        db.query(RiskFinding)
        .filter(
            RiskFinding.organization_id == organization_id,
            RiskFinding.status == "Open",
        )
        .order_by(RiskFinding.detected_at.desc())
        .all()
    )

    findings_by_asset = {}

    finding_severity_distribution = {
        "Critical": 0,
        "High": 0,
        "Medium": 0,
        "Low": 0,
    }

    open_operational_anomalies = 0

    for finding in open_findings:

        if finding.asset_id is not None:
            findings_by_asset.setdefault(
                finding.asset_id, []
            ).append(finding)

        severity = (
            finding.severity or ""
        ).strip().title()

        if severity in finding_severity_distribution:
            finding_severity_distribution[severity] += 1

        if (
            finding.category == "Operational Anomaly"
            or finding.source == "Statistical Anomaly Detection"
        ):
            open_operational_anomalies += 1

    # 5. Retrieve telemetry summaries

    metric_summary = get_metric_summary(
        db,
        organization_id
    )

    assets_with_telemetry = len(metric_summary)

    total_metric_observations = sum(
        item["observation_count"]
        for item in metric_summary.values()
    )

    # 6. Initialize analysis variables

    risk_distribution = {
        "Critical": 0,
        "High": 0,
        "Moderate": 0,
        "Low": 0,
    }

    trend_distribution = {
        "Increasing": 0,
        "Decreasing": 0,
        "Stable": 0,
        "Insufficient data": 0,
    }

    asset_analysis = []
    emerging_risk_signals = []

    weighted_change_total = 0.0
    total_change_weight = 0

    assets_with_history = 0
    assets_with_multiple_assessments = 0

    total_historical_assessments = len(assessments)

    valid_historical_assessments = sum(
        1
        for assessment in assessments
        if assessment.risk_score is not None
    )

    unassessed_assessments = (
        total_historical_assessments
        - valid_historical_assessments
    )

    increasing_assets = 0
    decreasing_assets = 0

    current_time = datetime.now(timezone.utc)

    # 7. Analyze each asset

    for asset in assets:

        asset_history = history_by_asset.get(
            asset.asset_id, []
        )

        valid_history = [
            assessment
            for assessment in asset_history
            if assessment.risk_score is not None
        ]

        criticality = (
            asset.criticality or "Medium"
        ).strip().lower()

        weight = CRITICALITY_WEIGHTS.get(
            criticality, 2
        )

        findings = findings_by_asset.get(
            asset.asset_id, []
        )

        severity_counts = {
            "Critical": 0,
            "High": 0,
            "Medium": 0,
            "Low": 0,
        }

        operational_anomaly_count = 0

        for finding in findings:

            severity = (
                finding.severity or ""
            ).strip().title()

            if severity in severity_counts:
                severity_counts[severity] += 1

            if (
                finding.category == "Operational Anomaly"
                or finding.source == "Statistical Anomaly Detection"
            ):
                operational_anomaly_count += 1

        # Current finding-based warning level

        if severity_counts["Critical"] > 0:
            finding_risk_level = "Critical"

        elif severity_counts["High"] > 0:
            finding_risk_level = "High"

        elif severity_counts["Medium"] > 0:
            finding_risk_level = "Moderate"

        elif severity_counts["Low"] > 0:
            finding_risk_level = "Low"

        else:
            finding_risk_level = "No open findings"

        # Historical risk trend

        if len(valid_history) >= 2:

            assets_with_multiple_assessments += 1

            previous_score = float(
                valid_history[-2].risk_score
            )

            latest_score = float(
                valid_history[-1].risk_score
            )

            score_change = round(
                latest_score - previous_score, 2
            )

            if score_change >= 5:
                trend = "Increasing"
                increasing_assets += 1

            elif score_change <= -5:
                trend = "Decreasing"
                decreasing_assets += 1

            else:
                trend = "Stable"

            weighted_change_total += score_change * weight
            total_change_weight += weight

        elif len(valid_history) == 1:

            latest_score = float(
                valid_history[-1].risk_score
            )

            score_change = None
            trend = "Insufficient data"

        else:

            latest_score = None
            score_change = None
            trend = "Insufficient data"

        if valid_history:

            assets_with_history += 1

            latest_level = classify_organization_risk(
                latest_score
            )

            risk_distribution[latest_level] += 1

        else:
            latest_level = "Not Assessed"

        trend_distribution[trend] += 1

        # Latest telemetry

        telemetry = metric_summary.get(asset.asset_id)

        latest_metric = (
            db.query(AssetMetric)
            .filter(
                AssetMetric.organization_id == organization_id,
                AssetMetric.asset_id == asset.asset_id,
            )
            .order_by(
                AssetMetric.observed_at.desc().nullslast(),
                AssetMetric.metric_id.desc(),
            )
            .first()
        )

        telemetry_status = "Unavailable"
        telemetry_age_hours = None
        latest_metric_values = None

        if telemetry and latest_metric:

            observed_at = latest_metric.observed_at

            if observed_at is not None:

                if observed_at.tzinfo is None:
                    observed_at = observed_at.replace(
                        tzinfo=timezone.utc
                    )

                telemetry_age_hours = round(
                    max(
                        0,
                        (
                            current_time - observed_at
                        ).total_seconds() / 3600
                    ),
                    2
                )

                telemetry_status = (
                    "Recent"
                    if telemetry_age_hours <= 24
                    else "Stale"
                )

            latest_metric_values = {
                "cpu_usage": (
                    float(latest_metric.cpu_usage)
                    if latest_metric.cpu_usage is not None
                    else None
                ),
                "memory_usage": (
                    float(latest_metric.memory_usage)
                    if latest_metric.memory_usage is not None
                    else None
                ),
                "disk_usage": (
                    float(latest_metric.disk_usage)
                    if latest_metric.disk_usage is not None
                    else None
                ),
                "network_in": (
                    float(latest_metric.network_in)
                    if latest_metric.network_in is not None
                    else None
                ),
                "network_out": (
                    float(latest_metric.network_out)
                    if latest_metric.network_out is not None
                    else None
                ),
            }

        # Emerging risk signals

        asset_signals = []

        if trend == "Increasing":
            asset_signals.append(
                "Historical risk score is increasing."
            )

        if severity_counts["Critical"] > 0:
            asset_signals.append(
                "One or more critical findings remain open."
            )

        if severity_counts["High"] > 0:
            asset_signals.append(
                "One or more high-severity findings remain open."
            )

        if operational_anomaly_count > 0:
            asset_signals.append(
                "Open operational anomalies require investigation."
            )

        if telemetry_status == "Stale":
            asset_signals.append(
                "Latest telemetry is more than 24 hours old."
            )

        if telemetry_status == "Unavailable":
            asset_signals.append(
                "No asset telemetry is available."
            )

        if asset_signals:

            emerging_risk_signals.append({
                "asset_id": asset.asset_id,
                "asset_name": asset.asset_name,
                "finding_risk_level": finding_risk_level,
                "historical_trend": trend,
                "open_findings": len(findings),
                "open_operational_anomalies": (
                    operational_anomaly_count
                ),
                "signals": asset_signals,
            })

        asset_analysis.append({
            "asset_id": asset.asset_id,
            "asset_name": asset.asset_name,
            "criticality": asset.criticality,
            "criticality_weight": weight,

            "assessment_count": len(asset_history),
            "valid_assessment_count": len(valid_history),
            "unassessed_assessment_count": (
                len(asset_history) - len(valid_history)
            ),

            "latest_risk_score": (
                round(latest_score, 2)
                if latest_score is not None
                else None
            ),
            "latest_risk_level": latest_level,
            "score_change": score_change,
            "historical_trend": trend,

            "open_findings": len(findings),
            "finding_severity_distribution": severity_counts,
            "open_operational_anomalies": (
                operational_anomaly_count
            ),
            "finding_risk_level": finding_risk_level,

            "telemetry_status": telemetry_status,
            "telemetry_observation_count": (
                telemetry["observation_count"]
                if telemetry
                else 0
            ),
            "latest_telemetry_observed_at": (
                telemetry["latest_observed_at"]
                if telemetry
                else None
            ),
            "telemetry_age_hours": telemetry_age_hours,
            "latest_metric_values": latest_metric_values,

            "emerging_risk_signals": asset_signals,
        })

    # 8. Calculate organization historical trend

    if total_change_weight > 0:

        organization_change = round(
            weighted_change_total / total_change_weight,
            2
        )

        if organization_change >= 5:
            organization_trend = "Increasing"

        elif organization_change <= -5:
            organization_trend = "Decreasing"

        else:
            organization_trend = "Stable"

    else:

        organization_change = None
        organization_trend = "Insufficient data"

    # 9. Determine historical data sufficiency

    if assets_with_multiple_assessments == 0:
        data_sufficiency = "Insufficient"

    elif assets_with_multiple_assessments < 5:
        data_sufficiency = "Low"

    elif assets_with_multiple_assessments < 10:
        data_sufficiency = "Moderate"

    else:
        data_sufficiency = "Good"

    # 10. Calculate current organization risk

    current_risk = calculate_organization_risk(
        db,
        organization_id
    )

    current_risk_posture = get_current_risk_posture(
        current_risk["risk_level"]
    )

    # 11. Determine emerging risk status

    emerging_risk_status = get_emerging_risk_status(
        finding_severity_distribution,
        open_operational_anomalies,
    )

    # 12. Organization outlook is based ONLY on historical trend

    organization_outlook = organization_trend

    # 13. Generate recommendations

    recommendations = []

    if finding_severity_distribution["Critical"] > 0:
        recommendations.append(
            "Immediately investigate and remediate open critical findings."
        )

    if finding_severity_distribution["High"] > 0:
        recommendations.append(
            "Prioritize remediation plans for open high-severity findings."
        )

    if open_operational_anomalies > 0:
        recommendations.append(
            "Investigate open operational anomalies before treating them as confirmed attacks."
        )

    if increasing_assets > 0:
        recommendations.append(
            "Review assets with increasing historical risk scores."
        )

    if decreasing_assets > 0:
        recommendations.append(
            "Maintain security improvements on assets with decreasing risk scores."
        )

    if assets_with_history < len(assets):
        recommendations.append(
            "Perform risk assessments for assets without valid assessment history."
        )

    if unassessed_assessments > 0:
        recommendations.append(
            "Review assessments without numerical risk scores and collect valid evidence."
        )

    if assets_with_telemetry < len(assets):
        recommendations.append(
            "Expand authorized telemetry collection to assets without monitoring data."
        )

    if data_sufficiency in ("Low", "Insufficient"):
        recommendations.append(
            "Collect more historical risk assessments before introducing supervised ML forecasting."
        )

    if not recommendations:
        recommendations.append(
            "Continue periodic risk assessments, monitoring and security control reviews."
        )

    # 14. Return integrated organization analysis

    return {
        "organization_id": organization_id,
        "organization_name": organization.organization_name,

        "organization_risk_score": current_risk["risk_score"],
        "organization_risk_level": current_risk["risk_level"],

        "organization_outlook": organization_outlook,
        "organization_historical_trend": organization_trend,
        "current_risk_posture": current_risk_posture,
        "emerging_risk_status": emerging_risk_status,
        "organization_risk_score_change": organization_change,

        "total_assets": len(assets),
        "assets_with_history": assets_with_history,
        "assets_without_history": len(assets) - assets_with_history,
        "assets_with_multiple_assessments": (
            assets_with_multiple_assessments
        ),

        "total_historical_assessments": total_historical_assessments,
        "valid_historical_assessments": valid_historical_assessments,
        "unassessed_assessments": unassessed_assessments,

        "risk_distribution": risk_distribution,
        "trend_distribution": trend_distribution,

        "open_findings": len(open_findings),
        "open_operational_anomalies": open_operational_anomalies,
        "finding_severity_distribution": (
            finding_severity_distribution
        ),

        "telemetry_summary": {
            "assets_with_telemetry": assets_with_telemetry,
            "assets_without_telemetry": (
                len(assets) - assets_with_telemetry
            ),
            "total_observations": total_metric_observations,
        },

        "data_sufficiency": data_sufficiency,

        "asset_analysis": asset_analysis,
        "emerging_risk_signals": emerging_risk_signals,

        "recommendations": recommendations,

        "analysis_method": (
            "Criticality-weighted historical risk trends, "
            "open security findings, statistical operational "
            "anomalies and asset telemetry"
        ),

        "prediction_status": (
            "Explainable rule-based risk outlook. "
            "Machine learning forecasting is not enabled."
        ),

        "disclaimer": (
            "Historical trend, current risk posture and emerging "
            "risk status are separate indicators. The outlook is "
            "not a guaranteed prediction of future incidents. "
            "Operational anomalies are not proof of cyberattacks. "
            "Missing risk scores and telemetry do not indicate zero risk."
        ),
    }
