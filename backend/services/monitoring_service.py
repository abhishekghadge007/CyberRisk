
import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from database import SessionLocal
from models import MonitoringSchedule, ScanJob
from services.nmap_service import execute_nmap_scan, validate_target
from services.vulnerability_service import analyze_scan_vulnerabilities


logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="UTC")


def process_due_monitoring_schedules():
    """Find and execute monitoring schedules that are due."""

    db = SessionLocal()

    try:
        now = datetime.now(timezone.utc)

        schedules = (
            db.query(MonitoringSchedule)
            .filter(
                MonitoringSchedule.is_enabled.is_(True),
                MonitoringSchedule.next_run_at <= now
            )
            .all()
        )

        monitoring_ids = [item.monitoring_id for item in schedules]

    finally:
        db.close()

    for monitoring_id in monitoring_ids:
        run_monitoring_schedule(monitoring_id)


def run_monitoring_schedule(monitoring_id):
    """Run one scheduled network scan and vulnerability analysis."""

    db = SessionLocal()
    scan_id = None

    try:
        schedule = (
            db.query(MonitoringSchedule)
            .filter(
                MonitoringSchedule.monitoring_id == monitoring_id,
                MonitoringSchedule.is_enabled.is_(True)
            )
            .first()
        )

        if not schedule:
            return

        now = datetime.now(timezone.utc)

        if schedule.next_run_at > now:
            return

        target = validate_target(schedule.target_network)

        scan = ScanJob(
            organization_id=schedule.organization_id,
            target_network=target,
            status="queued"
        )

        db.add(scan)
        db.flush()

        scan_id = scan.scan_id

        schedule.last_run_at = now
        schedule.next_run_at = now + timedelta(
            hours=schedule.interval_hours
        )
        schedule.last_scan_id = scan_id

        db.commit()

        logger.info(
            "Starting scheduled scan %s for monitoring schedule %s",
            scan_id,
            monitoring_id
        )

    except Exception:
        db.rollback()
        logger.exception(
            "Could not start monitoring schedule %s",
            monitoring_id
        )
        return

    finally:
        db.close()

    # Execute the existing Nmap scanner.
    execute_nmap_scan(scan_id)

    # Check the actual scan status because execute_nmap_scan
    # handles its own errors and does not re-raise them.
    analysis_db = SessionLocal()

    try:
        scan = (
            analysis_db.query(ScanJob)
            .filter(ScanJob.scan_id == scan_id)
            .first()
        )

        if not scan:
            logger.error("Scan %s was not found after execution", scan_id)
            return

        if scan.status == "completed":
            analyze_scan_vulnerabilities(analysis_db, scan_id)

            logger.info(
                "Vulnerability analysis completed for scan %s",
                scan_id
            )

        else:
            logger.warning(
                "Scheduled scan %s ended with status: %s",
                scan_id,
                scan.status
            )

    except Exception:
        analysis_db.rollback()
        logger.exception(
            "Post-scan vulnerability analysis failed for scan %s",
            scan_id
        )

    finally:
        analysis_db.close()


def start_scheduler():
    """Start the background monitoring scheduler."""

    if not scheduler.running:
        scheduler.add_job(
            process_due_monitoring_schedules,
            trigger="interval",
            seconds=60,
            id="continuous_monitoring",
            replace_existing=True,
            max_instances=1,
            coalesce=True
        )

        scheduler.start()
        logger.info("Continuous monitoring scheduler started")


def stop_scheduler():
    """Stop the background scheduler."""

    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Continuous monitoring scheduler stopped")
