
def generate_finding_recommendation(finding):
    """
    Generate explainable security recommendations
    using existing risk finding information.
    """

    category = (finding.category or "").strip().lower()
    title = (finding.title or "").strip()
    description = (finding.description or "").strip()
    severity = (finding.severity or "Medium").strip().lower()

    text_to_analyze = f"{title} {description}".lower()

    # Determine recommendation priority.
    if severity == "critical":
        priority = "Critical"
    elif severity == "high":
        priority = "High"
    elif severity == "medium":
        priority = "Medium"
    else:
        priority = "Low"

    # Vulnerability recommendations.
    if category == "vulnerability":

        action = [
            "Identify the affected software and exact version.",
            "Verify the CVE against the NVD and vendor security advisory.",
            "Apply the vendor-recommended security patch or upgrade.",
            "Restrict unnecessary network access to the affected service.",
            "Perform a vulnerability rescan after remediation."
        ]

        reason = (
            "An open vulnerability finding was detected. "
            "The affected software should be verified and remediated "
            "to reduce the possibility of exploitation."
        )

        if "router" in text_to_analyze:
            action.insert(
                0,
                "Verify the router model, firmware version and affected service."
            )

        if "remote code execution" in text_to_analyze:
            action.insert(
                0,
                "Prioritize investigation because remote code execution "
                "vulnerabilities can allow unauthorized code execution."
            )

    elif category in ["configuration", "misconfiguration"]:

        action = [
            "Review the affected system configuration.",
            "Compare the configuration against security best practices.",
            "Disable unnecessary services and insecure settings.",
            "Apply recommended configuration changes.",
            "Verify the changes through a security assessment."
        ]

        reason = (
            "A configuration-related security issue requires "
            "review and corrective action."
        )

    elif category in ["access control", "authentication"]:

        action = [
            "Review user accounts and access permissions.",
            "Enable multi-factor authentication where supported.",
            "Remove unnecessary privileges.",
            "Enforce strong authentication policies.",
            "Audit access logs after remediation."
        ]

        reason = (
            "Access control weaknesses can allow unauthorized "
            "users to access organizational resources."
        )

    elif category in ["network", "network security"]:

        action = [
            "Review exposed network ports and services.",
            "Restrict unnecessary inbound and outbound traffic.",
            "Review firewall and network access rules.",
            "Disable unused network services.",
            "Perform another authorized network scan."
        ]

        reason = (
            "Network security weaknesses may expose organizational "
            "systems to unauthorized access."
        )

    else:

        action = [
            "Investigate the reported security finding.",
            "Collect supporting logs and evidence.",
            "Identify the root cause.",
            "Apply an appropriate security control.",
            "Verify remediation and update the finding status."
        ]

        reason = (
            "A security finding requires investigation and "
            "appropriate remediation."
        )

    # Increase priority when likelihood and impact are high.
    likelihood = (
        float(finding.likelihood)
        if finding.likelihood is not None else None
    )

    impact = (
        float(finding.impact)
        if finding.impact is not None else None
    )

    if likelihood is not None and impact is not None:
        if likelihood >= 8 and impact >= 8:
            priority = "Critical"
        elif likelihood >= 7 and impact >= 7 and priority != "Critical":
            priority = "High"

    return {
        "finding_id": finding.finding_id,
        "asset_id": finding.asset_id,
        "finding_title": title,
        "category": finding.category,
        "severity": finding.severity,
        "likelihood": likelihood,
        "impact": impact,
        "priority": priority,
        "recommendation": reason,
        "recommended_actions": action,
        "reasoning": (
            f"Recommendation generated using finding category "
            f"'{finding.category}', severity '{finding.severity}', "
            f"and available likelihood and impact values."
        ),
        "recommendation_type": "Rule-Based Intelligent Recommendation"
    }


def generate_organization_recommendations(findings):

    recommendations = [
        generate_finding_recommendation(finding)
        for finding in findings
        if (finding.status or "").strip().lower() == "open"
    ]

    priority_order = {
        "Critical": 4,
        "High": 3,
        "Medium": 2,
        "Low": 1
    }

    recommendations.sort(
        key=lambda item: (
            priority_order[item["priority"]],
            (item["likelihood"] or 0) * (item["impact"] or 0)
        ),
        reverse=True
    )

    return {
        "total_recommendations": len(recommendations),
        "recommendations": recommendations,
        "methodology": "CyberRisk Explainable Recommendation Engine v1",
        "engine_type": "Rule-Based",
        "note": (
            "Recommendations are generated from existing findings. "
            "CVE remediation must be verified against the affected "
            "software version and vendor advisory."
        )
    }
