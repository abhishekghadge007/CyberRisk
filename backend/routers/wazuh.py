
import os
import hmac
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Header, Body
from sqlalchemy.orm import Session

from database import get_db
from models import Organization, Asset, RiskFinding


router = APIRouter(
    prefix="/api/wazuh",
    tags=["Wazuh Integration"]
)


def map_wazuh_severity(level: int):
    """
    Convert Wazuh rule levels (0-15) into CyberRisk severity.
    """

    if level >= 12:
        return "Critical", 9.0, 9.0

    if level >= 8:
        return "High", 7.0, 7.0

    if level >= 4:
        return "Medium", 4.0, 4.0

    return "Low", 2.0, 2.0


def verify_wazuh_token(token: str | None):
    """
    Require a configured shared secret for incoming alerts.
    """

    expected_token = os.getenv("WAZUH_WEBHOOK_TOKEN")

    if not expected_token:
        raise HTTPException(
            status_code=503,
            detail="WAZUH_WEBHOOK_TOKEN is not configured on the backend."
        )

    if not token or not hmac.compare_digest(token, expected_token):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing Wazuh integration token."
        )


@router.post("/alerts")
def receive_wazuh_alert(
    organization_id: int,
    payload: dict[str, Any] = Body(...),
    x_wazuh_token: str | None = Header(default=None),
    db: Session = Depends(get_db)
):
    """
    Receive a Wazuh JSON alert and convert it into a CyberRisk finding.

    Expected payload follows the standard Wazuh alert structure.
    """

    verify_wazuh_token(x_wazuh_token)

    organization = db.query(Organization).filter(
        Organization.organization_id == organization_id
    ).first()

    if not organization:
        raise HTTPException(
            status_code=404,
            detail="Organization not found."
        )

    agent = payload.get("agent") or {}
    rule = payload.get("rule") or {}

    if not isinstance(agent, dict) or not isinstance(rule, dict):
        raise HTTPException(
            status_code=400,
            detail="Invalid Wazuh alert: agent and rule must be objects."
        )

    alert_id = str(payload.get("id") or "").strip()

    if not alert_id:
        raise HTTPException(
            status_code=400,
            detail="Wazuh alert must contain an alert id."
        )

    try:
        rule_level = int(rule.get("level", 0))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="Wazuh rule level must be a number."
        )

    if not 0 <= rule_level <= 15:
        raise HTTPException(
            status_code=400,
            detail="Wazuh rule level must be between 0 and 15."
        )

    agent_name = str(agent.get("name") or "").strip()
    agent_ip = str(agent.get("ip") or "").strip()

    # Locate the corresponding asset within this organization.
    asset_query = db.query(Asset).filter(
        Asset.organization_id == organization_id
    )

    asset = None

    if agent_ip and agent_ip.lower() not in ("any", "unknown", "n/a"):
        asset = asset_query.filter(
            Asset.ip_address == agent_ip
        ).first()

    if not asset and agent_name:
        asset = asset_query.filter(
            (Asset.hostname.ilike(agent_name)) |
            (Asset.asset_name.ilike(agent_name))
        ).first()

    if not asset:
        raise HTTPException(
            status_code=404,
            detail=(
                "No matching asset found for this Wazuh agent. "
                "Register the asset or update its IP address/hostname first."
            )
        )

    severity, likelihood, impact = map_wazuh_severity(rule_level)

    rule_id = str(rule.get("id") or "Unknown")
    rule_description = str(
        rule.get("description") or "Wazuh security alert"
    )

    title = f"Wazuh Alert: {rule_description}"[:255]

    evidence = {
        "integration": "Wazuh",
        "wazuh_alert_id": alert_id,
        "agent": agent,
        "rule": rule,
        "manager": payload.get("manager"),
        "timestamp": payload.get("timestamp"),
        "location": payload.get("location"),
        "decoder": payload.get("decoder"),
        "full_log": payload.get("full_log"),
        "original_alert": payload
    }

    # Avoid creating duplicate findings for repeated delivery
    # of the same Wazuh alert ID.
    existing_finding = db.query(RiskFinding).filter(
        RiskFinding.organization_id == organization_id,
        RiskFinding.asset_id == asset.asset_id,
        RiskFinding.source == "Wazuh",
        RiskFinding.evidence["wazuh_alert_id"].astext == alert_id
    ).first()

    if existing_finding:
        existing_finding.last_seen = datetime.now(timezone.utc)
        existing_finding.evidence = evidence

        db.commit()
        db.refresh(existing_finding)

        return {
            "message": "Existing Wazuh finding updated.",
            "duplicate": True,
            "finding": {
                "finding_id": existing_finding.finding_id,
                "organization_id": existing_finding.organization_id,
                "asset_id": existing_finding.asset_id,
                "asset_name": asset.asset_name,
                "source": existing_finding.source,
                "title": existing_finding.title,
                "severity": existing_finding.severity,
                "status": existing_finding.status
            }
        }

    finding = RiskFinding(
        organization_id=organization_id,
        asset_id=asset.asset_id,
        category="Endpoint Security",
        source="Wazuh",
        title=title,
        description=rule_description,
        severity=severity,
        likelihood=likelihood,
        impact=impact,
        evidence=evidence
    )

    db.add(finding)
    db.commit()
    db.refresh(finding)

    return {
        "message": "Wazuh alert successfully imported into CyberRisk.",
        "duplicate": False,
        "finding": {
            "finding_id": finding.finding_id,
            "organization_id": finding.organization_id,
            "asset_id": finding.asset_id,
            "asset_name": asset.asset_name,
            "source": finding.source,
            "title": finding.title,
            "severity": finding.severity,
            "likelihood": float(finding.likelihood),
            "impact": float(finding.impact),
            "status": finding.status
        }
    }
