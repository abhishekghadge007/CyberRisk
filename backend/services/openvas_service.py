
import hashlib
import ipaddress
import xml.etree.ElementTree as ET

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models import (
    Organization,
    Asset,
    Vulnerability,
    AssetVulnerability,
    RiskFinding
)


# ==========================================
# 1. OPENVAS SEVERITY MAPPING
# ==========================================

def map_openvas_severity(score):

    try:
        score = float(score)
    except (TypeError, ValueError):
        score = 0.0

    if score >= 9.0:
        return "Critical"

    if score >= 7.0:
        return "High"

    if score >= 4.0:
        return "Medium"

    if score > 0:
        return "Low"

    return "Unknown"


# ==========================================
# 2. LIKELIHOOD AND IMPACT ESTIMATION
# ==========================================

def estimate_openvas_risk(cvss_score):

    try:
        score = float(cvss_score)
    except (TypeError, ValueError):
        return 5.0, 5.0

    if score >= 9:
        return 9.0, 10.0

    if score >= 7:
        return 8.0, 8.0

    if score >= 4:
        return 6.0, 6.0

    if score > 0:
        return 4.0, 4.0

    return 5.0, 5.0


# ==========================================
# 3. XML HELPER
# ==========================================

def get_text(element, path, default=""):

    if element is None:
        return default

    node = element.find(path)

    if node is None or node.text is None:
        return default

    return node.text.strip()


# ==========================================
# 4. PARSE OPENVAS XML REPORT
# ==========================================

def parse_openvas_report(xml_content):

    if not xml_content or not xml_content.strip():
        raise ValueError("OpenVAS XML report is empty.")

    try:
        root = ET.fromstring(xml_content)

    except ET.ParseError as error:
        raise ValueError(
            f"Invalid OpenVAS XML report: {str(error)}"
        )

    results = root.findall(".//result")

    if not results:
        raise ValueError(
            "No vulnerability results were found in the XML report."
        )

    parsed_results = []

    for result in results:

        host_element = result.find("host")

        if host_element is None:
            continue

        host_ip = get_text(
            host_element,
            "ip"
        )

        if not host_ip:
            continue

        try:
            host_ip = str(ipaddress.ip_address(host_ip))
        except ValueError:
            continue

        nvt = result.find("nvt")

        if nvt is None:
            continue

        oid = nvt.get("oid", "")

        name = get_text(
            nvt,
            "name",
            "OpenVAS vulnerability"
        )

        description = get_text(
            result,
            "description"
        )

        if not description:
            description = get_text(
                nvt,
                "tags"
            )

        raw_severity = get_text(
            result,
            "severity",
            "0"
        )

        try:
            cvss_score = float(raw_severity)
        except (TypeError, ValueError):
            cvss_score = 0.0

        severity = map_openvas_severity(cvss_score)

        cve_ids = []

        # Extract CVEs from standard NVT references.
        for reference in nvt.findall(".//ref"):

            reference_type = reference.get("type", "").upper()

            reference_id = reference.get("id", "").strip()

            if (
                reference_type == "CVE"
                and reference_id.startswith("CVE-")
            ):
                cve_ids.append(reference_id)

        # Also inspect the CVE field when provided.
        cve_text = get_text(nvt, "cve")

        if cve_text and cve_text.upper() not in ("N/A", "NONE"):
            for item in cve_text.replace(",", " ").split():

                item = item.strip()

                if item.upper().startswith("CVE-"):
                    cve_ids.append(item.upper())

        cve_ids = sorted(set(cve_ids))

        port = get_text(
            result,
            "port"
        )

        host_name = get_text(
            host_element,
            "hostname"
        )

        result_id = get_text(
            result,
            "id"
        )

        parsed_results.append({
            "host_ip": host_ip,
            "hostname": host_name,
            "oid": oid,
            "name": name[:255],
            "description": description[:10000],
            "cvss_score": cvss_score,
            "severity": severity,
            "cve_ids": cve_ids,
            "port": port,
            "result_id": result_id
        })

    if not parsed_results:
        raise ValueError(
            "The XML report contains no usable vulnerability results."
        )

    return parsed_results


# ==========================================
# 5. MATCH OPENVAS HOST TO CYBERRISK ASSET
# ==========================================

def find_matching_asset(db, organization_id, host_ip):

    return db.query(Asset).filter(
        Asset.organization_id == organization_id,
        Asset.ip_address == host_ip
    ).first()


# ==========================================
# 6. SAVE CVE INFORMATION WHEN AVAILABLE
# ==========================================

def save_cve_link(
    db,
    asset_id,
    cve_id,
    title,
    description,
    severity,
    cvss_score
):

    vulnerability = db.query(Vulnerability).filter(
        Vulnerability.cve_id == cve_id
    ).first()

    if not vulnerability:

        vulnerability = Vulnerability(
            cve_id=cve_id,
            title=title[:255],
            description=description,
            severity=severity,
            cvss_score=cvss_score
        )

        db.add(vulnerability)
        db.flush()

    existing_link = db.query(AssetVulnerability).filter(
        AssetVulnerability.asset_id == asset_id,
        AssetVulnerability.vulnerability_id ==
        vulnerability.vulnerability_id
    ).first()

    if not existing_link:

        db.add(
            AssetVulnerability(
                asset_id=asset_id,
                vulnerability_id=vulnerability.vulnerability_id,
                status="Open"
            )
        )


# ==========================================
# 7. CREATE OR UPDATE RISK FINDING
# ==========================================

def save_openvas_finding(
    db,
    organization_id,
    asset,
    item
):

    cve_ids = item["cve_ids"]

    # Stable identity for CVE and non-CVE findings.
    identity = (
        ",".join(cve_ids)
        if cve_ids
        else item["oid"] or item["name"]
    )

    identity_hash = hashlib.sha256(
        identity.encode("utf-8")
    ).hexdigest()

    evidence = {
        "source": "OpenVAS",
        "scanner": "Greenbone/OpenVAS",
        "host_ip": item["host_ip"],
        "hostname": item["hostname"],
        "oid": item["oid"],
        "result_id": item["result_id"],
        "port": item["port"],
        "cve_ids": cve_ids,
        "cvss_score": item["cvss_score"],
        "identity_hash": identity_hash,
        "description": item["description"],
        "scoring_note": (
            "Likelihood and impact are project-defined estimates "
            "based on the reported CVSS score, not measured "
            "real-world probabilities."
        )
    }

    title = f"OpenVAS: {item['name']}"[:255]

    existing_finding = db.query(RiskFinding).filter(
        RiskFinding.organization_id == organization_id,
        RiskFinding.asset_id == asset.asset_id,
        RiskFinding.source == "OpenVAS",
        RiskFinding.evidence["identity_hash"].astext ==
        identity_hash,
        RiskFinding.status == "Open"
    ).first()

    likelihood, impact = estimate_openvas_risk(
        item["cvss_score"]
    )

    if existing_finding:

        existing_finding.last_seen = datetime.now(timezone.utc)
        existing_finding.evidence = evidence
        existing_finding.severity = item["severity"]
        existing_finding.description = item["description"]
        existing_finding.likelihood = likelihood
        existing_finding.impact = impact

        return "updated"

    finding = RiskFinding(
        organization_id=organization_id,
        asset_id=asset.asset_id,
        category="Vulnerability",
        source="OpenVAS",
        title=title,
        description=item["description"],
        severity=item["severity"],
        likelihood=likelihood,
        impact=impact,
        status="Open",
        evidence=evidence
    )

    db.add(finding)

    return "created"


# ==========================================
# 8. IMPORT OPENVAS REPORT
# ==========================================

def import_openvas_report(
    db: Session,
    organization_id: int,
    xml_content: str
):

    organization = db.query(Organization).filter(
        Organization.organization_id == organization_id
    ).first()

    if not organization:
        raise ValueError("Organization not found.")

    parsed_results = parse_openvas_report(xml_content)

    created_count = 0
    updated_count = 0
    skipped_count = 0
    unmatched_hosts = set()

    try:

        for item in parsed_results:

            asset = find_matching_asset(
                db,
                organization_id,
                item["host_ip"]
            )

            if not asset:

                unmatched_hosts.add(item["host_ip"])
                skipped_count += 1
                continue

            # Store CVE records and asset relationships
            for cve_id in item["cve_ids"]:

                save_cve_link(
                    db=db,
                    asset_id=asset.asset_id,
                    cve_id=cve_id,
                    title=item["name"],
                    description=item["description"],
                    severity=item["severity"],
                    cvss_score=item["cvss_score"]
                )

            result = save_openvas_finding(
                db,
                organization_id,
                asset,
                item
            )

            if result == "created":
                created_count += 1

            elif result == "updated":
                updated_count += 1

        db.commit()

    except Exception:

        db.rollback()
        raise

    return {
        "message": "OpenVAS report imported successfully.",
        "organization_id": organization_id,
        "total_report_results": len(parsed_results),
        "findings_created": created_count,
        "findings_updated": updated_count,
        "unmatched_results_skipped": skipped_count,
        "unmatched_host_ips": sorted(unmatched_hosts)
    }
