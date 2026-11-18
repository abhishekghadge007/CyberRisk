
import ipaddress
import logging
import shutil
import subprocess
import xml.etree.ElementTree as ET

from datetime import datetime, timezone

from sqlalchemy import func

from database import SessionLocal
from models import ScanJob, ScanResult, Asset


logger = logging.getLogger(__name__)


# ==========================================
# 1. HELPER: FORMAT PROCESS OUTPUT
# ==========================================

def format_output(value):

    if value is None:
        return ""

    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace").strip()

    return str(value).strip()


# ==========================================
# 2. VALIDATE SCAN TARGET
# ==========================================

def validate_target(target):

    try:
        network = ipaddress.ip_network(target, strict=False)

        if network.version != 4:
            raise ValueError("Only IPv4 targets are supported.")

        allowed_networks = [
            ipaddress.ip_network("10.0.0.0/8"),
            ipaddress.ip_network("172.16.0.0/12"),
            ipaddress.ip_network("192.168.0.0/16")
        ]

        is_allowed = (
            network.is_loopback
            or any(
                network.subnet_of(allowed)
                for allowed in allowed_networks
            )
        )

        if not is_allowed:
            raise ValueError(
                "Only localhost or RFC1918 private IPv4 networks are allowed."
            )

        if network.num_addresses > 256:
            raise ValueError(
                "Maximum scan range is 256 addresses."
            )

        return str(network)

    except ValueError as error:
        raise ValueError(str(error))


# ==========================================
# 3. AUTOMATIC ASSET DISCOVERY
# ==========================================

def discover_or_update_asset(db, organization_id, address, hostname):

    now = datetime.now(timezone.utc)

    try:
        normalized_ip = str(ipaddress.ip_address(address))

    except ValueError:
        logger.warning(
            "Ignoring invalid discovered IP: %s",
            address
        )
        return None

    if ipaddress.ip_address(normalized_ip).is_loopback:
        logger.warning(
            "Ignoring localhost address: %s",
            normalized_ip
        )
        return None

    # Find an existing asset using organization + IP.
    asset = db.query(Asset).filter(
        Asset.organization_id == organization_id,
        func.host(Asset.ip_address) == normalized_ip
    ).first()

    if asset:

        asset.last_seen = now
        asset.updated_at = now

        if hostname:
            asset.hostname = hostname
            asset.asset_name = hostname

        db.flush()

        logger.info(
            "Existing asset updated: asset_id=%s IP=%s",
            asset.asset_id,
            normalized_ip
        )

        return asset

    # Create a newly discovered asset.
    asset = Asset(
        organization_id=organization_id,
        asset_name=hostname or normalized_ip,
        asset_type="Unknown",
        ip_address=normalized_ip,
        hostname=hostname,
        criticality="Medium",
        environment="Discovered",
        last_seen=now,
        updated_at=now
    )

    db.add(asset)
    db.flush()

    logger.info(
        "New asset discovered: asset_id=%s IP=%s",
        asset.asset_id,
        normalized_ip
    )

    return asset


# ==========================================
# 4. EXTRACT SERVICE INFORMATION
# ==========================================

def extract_service_information(port):

    service = port.find("service")

    if service is None:
        return {
            "service_name": None,
            "product": None,
            "version": None,
            "extra_info": None
        }

    return {
        "service_name": service.get("name"),
        "product": service.get("product"),
        "version": service.get("version"),
        "extra_info": service.get("extrainfo")
    }


# ==========================================
# 5. EXECUTE NMAP SCAN
# ==========================================

def execute_nmap_scan(scan_id):

    db = SessionLocal()

    try:

        logger.info("========================================")
        logger.info(
            "Starting Nmap scan: scan_id=%s",
            scan_id
        )

        # Find requested scan.
        scan = db.query(ScanJob).filter(
            ScanJob.scan_id == scan_id
        ).first()

        if not scan:
            logger.error(
                "Scan job not found: scan_id=%s",
                scan_id
            )
            return

        # Parse the exact requested scan range.
        scan_network = ipaddress.ip_network(
            scan.target_network,
            strict=False
        )

        if scan_network.version != 4:
            raise ValueError(
                "Only IPv4 scan targets are supported."
            )

        # Update scan status.
        scan.status = "running"
        scan.started_at = datetime.now(timezone.utc)
        scan.error_message = None

        db.commit()

        # ----------------------------------
        # Locate Nmap
        # ----------------------------------

        nmap_path = shutil.which("nmap")

        if not nmap_path:
            raise RuntimeError(
                "Nmap is not installed or not available in PATH."
            )

        logger.info(
            "Nmap executable: %s",
            nmap_path
        )

        logger.info(
            "Target network: %s",
            scan_network
        )

        # ----------------------------------
        # Nmap command
        # ----------------------------------

        command = [
            nmap_path,
            "-sV",
            "--version-intensity", "9",
            "--top-ports", "100",
            "-T3",
            "-oX", "-",
            str(scan_network)
        ]

        logger.info(
            "Executing Nmap command: %s",
            " ".join(command)
        )

        # ----------------------------------
        # Execute Nmap
        # ----------------------------------

        try:

            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=600,
                errors="replace"
            )

        except subprocess.TimeoutExpired as error:

            stdout = format_output(error.stdout)
            stderr = format_output(error.stderr)

            logger.error(
                "Nmap timeout: scan_id=%s timeout=600 seconds",
                scan_id
            )

            if stderr:
                logger.error(
                    "Nmap timeout stderr: %s",
                    stderr[-4000:]
                )

            if stdout:
                logger.error(
                    "Nmap partial output: %s",
                    stdout[-2000:]
                )

            raise RuntimeError(
                "Nmap scan exceeded the 600-second timeout. "
                + stderr[-1500:]
            )

        # ----------------------------------
        # Check Nmap result
        # ----------------------------------

        logger.info(
            "Nmap process completed: return_code=%s",
            process.returncode
        )

        if process.stderr.strip():
            logger.warning(
                "Nmap stderr: %s",
                process.stderr[-4000:]
            )

        if process.returncode != 0:

            error_details = (
                process.stderr.strip()
                or process.stdout.strip()
                or "Nmap returned a non-zero exit code."
            )

            raise RuntimeError(
                f"Nmap failed with return code {process.returncode}: "
                f"{error_details[-1500:]}"
            )

        if not process.stdout.strip():
            raise RuntimeError(
                "Nmap returned empty XML output."
            )

        # ----------------------------------
        # Parse Nmap XML
        # ----------------------------------

        try:

            root = ET.fromstring(process.stdout)

        except ET.ParseError as error:

            logger.exception(
                "Nmap XML parsing failed"
            )

            raise RuntimeError(
                f"Invalid Nmap XML output: {error}"
            )

        hosts = root.findall("host")

        logger.info(
            "Nmap XML parsed successfully. Hosts reported: %s",
            len(hosts)
        )

        discovered_hosts = 0
        discovered_ports = 0
        skipped_hosts = 0

        # ----------------------------------
        # Process discovered hosts
        # ----------------------------------

        for host in hosts:

            host_status = host.find("status")

            if (
                host_status is None
                or host_status.get("state") != "up"
            ):
                continue

            # Extract IPv4 address.
            address = None

            for item in host.findall("address"):

                if item.get("addrtype") == "ipv4":
                    address = item.get("addr")
                    break

            if not address:
                continue

            # Validate discovered IP.
            try:

                host_ip = ipaddress.ip_address(address)

            except ValueError:

                logger.warning(
                    "Skipping invalid discovered IP: %s",
                    address
                )

                skipped_hosts += 1
                continue

            # Ensure discovered IP belongs to requested range.
            if host_ip not in scan_network:

                logger.warning(
                    "Skipping IP outside scan range: %s",
                    address
                )

                skipped_hosts += 1
                continue

            # Ignore network and broadcast addresses
            # for subnets larger than /31.
            #
            # /32: one individual host.
            # /31: both addresses are usable.
            # /30 and larger: exclude network/broadcast.

            if scan_network.num_addresses > 2:

                if host_ip == scan_network.network_address:

                    logger.warning(
                        "Skipping network address: %s",
                        address
                    )

                    skipped_hosts += 1
                    continue

                if host_ip == scan_network.broadcast_address:

                    logger.warning(
                        "Skipping broadcast address: %s",
                        address
                    )

                    skipped_hosts += 1
                    continue

            # Extract hostname.
            hostname_element = host.find(
                "./hostnames/hostname"
            )

            hostname = (
                hostname_element.get("name")
                if hostname_element is not None
                else None
            )

            # Automatically discover or update asset.
            asset = discover_or_update_asset(
                db,
                scan.organization_id,
                address,
                hostname
            )

            if asset is None:

                logger.warning(
                    "Host skipped during asset registration: %s",
                    address
                )

                skipped_hosts += 1
                continue

            discovered_hosts += 1

            # Extract open ports.
            open_ports = []

            for port in host.findall("./ports/port"):

                state_element = port.find("state")

                if (
                    state_element is not None
                    and state_element.get("state") == "open"
                ):
                    open_ports.append(port)

            # Save host even if no open ports were discovered.
            if not open_ports:

                db.add(ScanResult(
                    scan_id=scan.scan_id,
                    asset_id=asset.asset_id,
                    ip_address=address,
                    hostname=hostname,
                    state="host_up"
                ))

            # Save every discovered open port.
            for port in open_ports:

                service_info = extract_service_information(port)

                db.add(ScanResult(
                    scan_id=scan.scan_id,
                    asset_id=asset.asset_id,
                    ip_address=address,
                    hostname=hostname,
                    port=int(port.get("portid")),
                    protocol=port.get("protocol"),
                    state="open",
                    service_name=service_info["service_name"],
                    product=service_info["product"],
                    version=service_info["version"],
                    extra_info=service_info["extra_info"]
                ))

                discovered_ports += 1

                logger.info(
                    "Open port: IP=%s port=%s service=%s product=%s version=%s",
                    address,
                    port.get("portid"),
                    service_info["service_name"],
                    service_info["product"],
                    service_info["version"]
                )

        # ----------------------------------
        # Complete scan
        # ----------------------------------

        scan.status = "completed"
        scan.completed_at = datetime.now(timezone.utc)
        scan.error_message = None

        db.commit()

        logger.info(
            "Nmap scan completed successfully: "
            "scan_id=%s hosts=%s open_ports=%s skipped_hosts=%s",
            scan_id,
            discovered_hosts,
            discovered_ports,
            skipped_hosts
        )

        logger.info("========================================")

    except Exception as error:

        db.rollback()

        logger.exception(
            "Nmap scan failed: scan_id=%s error=%s",
            scan_id,
            str(error)
        )

        # Save failed scan status.
        try:

            scan = db.query(ScanJob).filter(
                ScanJob.scan_id == scan_id
            ).first()

            if scan:

                scan.status = "failed"
                scan.completed_at = datetime.now(timezone.utc)
                scan.error_message = str(error)[:2000]

                db.commit()

        except Exception:

            db.rollback()

            logger.exception(
                "Could not save failed scan status: scan_id=%s",
                scan_id
            )

    finally:

        db.close()

        logger.info(
            "Nmap scan process finished: scan_id=%s",
            scan_id
        )
