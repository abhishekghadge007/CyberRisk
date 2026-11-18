
from datetime import datetime, timezone
from statistics import median

from sqlalchemy.orm import Session

from models import Asset, AssetMetric, RiskFinding


# ==========================================
# CONFIGURATION
# ==========================================

BASELINE_SIZE = 10
ANOMALY_THRESHOLD = 3.5

CATEGORY = "Operational Anomaly"
SOURCE = "Statistical Anomaly Detection"


# ==========================================
# METRIC CONFIGURATION
# ==========================================

METRICS = {
    "cpu_usage": {
        "title": "Unusual CPU Usage Detected",
        "unit": "%",
        "minimum_change": 15.0,
        "impact": 6
    },
    "memory_usage": {
        "title": "Unusual Memory Usage Detected",
        "unit": "%",
        "minimum_change": 10.0,
        "impact": 6
    },
    "disk_usage": {
        "title": "Unusual Disk Usage Detected",
        "unit": "%",
        "minimum_change": 5.0,
        "impact": 5
    },
    "network_in": {
        "title": "Unusual Incoming Network Traffic Detected",
        "unit": "bytes/second",
        "minimum_change": 1024.0,
        "impact": 5
    },
    "network_out": {
        "title": "Unusual Outgoing Network Traffic Detected",
        "unit": "bytes/second",
        "minimum_change": 1024.0,
        "impact": 5
    }
}


# ==========================================
# SEVERITY CLASSIFICATION
# ==========================================

def classify_severity(anomaly_score):

    if anomaly_score >= 6.0:
        return "Critical"

    if anomaly_score >= 4.5:
        return "High"

    return "Medium"


# ==========================================
# CALCULATE ROBUST ANOMALY SCORE
# ==========================================

def calculate_anomaly_score(
    current_value,
    historical_values,
    minimum_change
):

    historical_median = median(historical_values)

    absolute_deviations = [
        abs(value - historical_median)
        for value in historical_values
    ]

    mad = median(absolute_deviations)

    difference = abs(current_value - historical_median)

    if mad == 0:

        if difference < minimum_change:
            return None, historical_median, mad

        anomaly_score = (
            3.5 * difference / minimum_change
        )

    else:

        anomaly_score = (
            0.6745 * difference / mad
        )

    if anomaly_score < ANOMALY_THRESHOLD:
        return None, historical_median, mad

    return anomaly_score, historical_median, mad


# ==========================================
# SAVE OR UPDATE ANOMALY FINDING
# ==========================================

def save_anomaly_finding(
    db,
    organization_id,
    asset_id,
    metric_name,
    metric_config,
    current_value,
    historical_median,
    mad,
    anomaly_score,
    metric_record
):

    severity = classify_severity(anomaly_score)

    likelihood = min(
        10,
        max(1, round(5 + min(anomaly_score, 10) / 2))
    )

    title = metric_config["title"]

    description = (
        f"{metric_name} showed unusual behaviour. "
        f"Current value: {current_value} "
        f"{metric_config['unit']}. "
        f"Historical median: {historical_median} "
        f"{metric_config['unit']}. "
        f"Robust anomaly score: {anomaly_score:.2f}."
    )

    evidence = {
        "detection_method": "Median Absolute Deviation",
        "metric_name": metric_name,
        "current_value": current_value,
        "historical_median": historical_median,
        "historical_mad": mad,
        "anomaly_score": round(anomaly_score, 2),
        "baseline_samples": BASELINE_SIZE,
        "unit": metric_config["unit"],
        "metric_id": metric_record.metric_id,
        "observed_at": (
            metric_record.observed_at.isoformat()
            if metric_record.observed_at
            else None
        )
    }

    # Find an existing open finding.
    existing_finding = db.query(RiskFinding).filter(
        RiskFinding.organization_id == organization_id,
        RiskFinding.asset_id == asset_id,
        RiskFinding.category == CATEGORY,
        RiskFinding.source == SOURCE,
        RiskFinding.title == title,
        RiskFinding.status.ilike("open")
    ).first()

    if existing_finding:

        existing_finding.description = description
        existing_finding.severity = severity
        existing_finding.likelihood = likelihood
        existing_finding.impact = metric_config["impact"]
        existing_finding.evidence = evidence
        existing_finding.last_seen = datetime.now(timezone.utc)

        return {
            "finding_id": existing_finding.finding_id,
            "action": "updated",
            "title": title,
            "severity": severity
        }

    # Create a new finding if no open finding exists.
    new_finding = RiskFinding(
        organization_id=organization_id,
        asset_id=asset_id,
        category=CATEGORY,
        source=SOURCE,
        title=title,
        description=description,
        severity=severity,
        likelihood=likelihood,
        impact=metric_config["impact"],
        status="Open",
        evidence=evidence
    )

    db.add(new_finding)
    db.flush()

    return {
        "finding_id": new_finding.finding_id,
        "action": "created",
        "title": title,
        "severity": severity
    }


# ==========================================
# AUTOMATICALLY RESOLVE NORMAL ANOMALIES
# ==========================================

def resolve_anomaly_finding(
    db,
    organization_id,
    asset_id,
    metric_config
):

    title = metric_config["title"]

    existing_finding = db.query(RiskFinding).filter(
        RiskFinding.organization_id == organization_id,
        RiskFinding.asset_id == asset_id,
        RiskFinding.category == CATEGORY,
        RiskFinding.source == SOURCE,
        RiskFinding.title == title,
        RiskFinding.status.ilike("open")
    ).first()

    if not existing_finding:
        return None

    existing_finding.status = "Resolved"
    existing_finding.resolved_at = datetime.now(timezone.utc)

    return {
        "finding_id": existing_finding.finding_id,
        "title": title,
        "action": "resolved"
    }


# ==========================================
# MAIN ANOMALY DETECTION ENGINE
# ==========================================

def analyze_asset_anomalies(
    db: Session,
    organization_id: int,
    asset_id: int
):

    # Verify asset ownership.
    asset = db.query(Asset).filter(
        Asset.asset_id == asset_id,
        Asset.organization_id == organization_id
    ).first()

    if not asset:
        raise ValueError(
            "Asset not found in the specified organization."
        )

    # Fetch latest observation + historical baseline.
    records = db.query(AssetMetric).filter(
        AssetMetric.organization_id == organization_id,
        AssetMetric.asset_id == asset_id
    ).order_by(
        AssetMetric.observed_at.desc(),
        AssetMetric.metric_id.desc()
    ).limit(BASELINE_SIZE + 1).all()

    # Do not create or resolve findings without enough data.
    if len(records) < BASELINE_SIZE + 1:

        return {
            "status": "insufficient_data",
            "organization_id": organization_id,
            "asset_id": asset_id,
            "available_observations": len(records),
            "required_observations": BASELINE_SIZE + 1,
            "message": (
                f"At least {BASELINE_SIZE + 1} observations "
                "are required for anomaly detection."
            ),
            "anomalies": []
        }

    current_record = records[0]
    historical_records = records[1:]

    results = []
    anomalies = []
    skipped_metrics = []
    resolved_findings = []

    # Analyze every configured metric.
    for metric_name, config in METRICS.items():

        current_raw = getattr(current_record, metric_name)

        if current_raw is None:

            skipped_metrics.append({
                "metric": metric_name,
                "reason": "Latest metric value is missing."
            })

            continue

        current_value = float(current_raw)

        historical_values = [
            float(getattr(record, metric_name))
            for record in historical_records
            if getattr(record, metric_name) is not None
        ]

        if len(historical_values) < BASELINE_SIZE:

            skipped_metrics.append({
                "metric": metric_name,
                "reason": "Insufficient historical values.",
                "available_samples": len(historical_values),
                "required_samples": BASELINE_SIZE
            })

            continue

        anomaly_score, historical_median, mad = (
            calculate_anomaly_score(
                current_value,
                historical_values,
                config["minimum_change"]
            )
        )

        # ======================================
        # NORMAL METRIC: CHECK FOR RESOLUTION
        # ======================================

        if anomaly_score is None:

            results.append({
                "metric": metric_name,
                "status": "normal",
                "current_value": current_value,
                "historical_median": historical_median
            })

            resolution = resolve_anomaly_finding(
                db=db,
                organization_id=organization_id,
                asset_id=asset_id,
                metric_config=config
            )

            if resolution:
                resolved_findings.append(resolution)

            continue

        # ======================================
        # ANOMALY DETECTED
        # ======================================

        finding_result = save_anomaly_finding(
            db=db,
            organization_id=organization_id,
            asset_id=asset_id,
            metric_name=metric_name,
            metric_config=config,
            current_value=current_value,
            historical_median=historical_median,
            mad=mad,
            anomaly_score=anomaly_score,
            metric_record=current_record
        )

        anomaly = {
            "metric": metric_name,
            "current_value": current_value,
            "historical_median": historical_median,
            "anomaly_score": round(anomaly_score, 2),
            "severity": finding_result["severity"],
            **finding_result
        }

        anomalies.append(anomaly)

    # ==========================================
    # COMMIT DATABASE CHANGES
    # ==========================================

    if anomalies or resolved_findings:
        db.commit()
    else:
        db.rollback()

    # ==========================================
    # FINAL RESPONSE
    # ==========================================

    return {
        "status": "completed",
        "organization_id": organization_id,
        "asset_id": asset_id,
        "asset_name": asset.asset_name,
        "baseline_observations": BASELINE_SIZE,
        "anomalies_detected": len(anomalies),
        "normal_metrics": len(results),
        "anomalies_resolved": len(resolved_findings),
        "resolved_findings": resolved_findings,
        "skipped_metrics": skipped_metrics,
        "anomalies": anomalies,
        "message": "Statistical anomaly analysis completed."
    }
