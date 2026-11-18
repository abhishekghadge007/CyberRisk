from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models import Organization, MonitoringSchedule
from schemas import (
    MonitoringScheduleCreate,
    MonitoringScheduleResponse
)
from services.nmap_service import validate_target


router = APIRouter(
    prefix="/api/monitoring",
    tags=["Continuous Monitoring"]
)


# CREATE MONITORING SCHEDULE

@router.post(
    "/schedules",
    response_model=MonitoringScheduleResponse,
    status_code=201
)
def create_monitoring_schedule(
    request: MonitoringScheduleCreate,
    db: Session = Depends(get_db)
):
    organization = (
        db.query(Organization)
        .filter(
            Organization.organization_id == request.organization_id
        )
        .first()
    )

    if not organization:
        raise HTTPException(
            status_code=404,
            detail="Organization not found"
        )

    try:
        target = validate_target(request.target_network)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    now = datetime.now(timezone.utc)

    schedule = MonitoringSchedule(
        organization_id=request.organization_id,
        target_network=target,
        interval_hours=request.interval_hours,
        is_enabled=True,
        next_run_at=now + timedelta(
            hours=request.interval_hours
        )
    )

    try:
        db.add(schedule)
        db.commit()
        db.refresh(schedule)

        return schedule

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A monitoring schedule already exists for this organization and network."
        )


# VIEW MONITORING SCHEDULES

@router.get(
    "/schedules",
    response_model=list[MonitoringScheduleResponse]
)
def get_monitoring_schedules(
    organization_id: int = None,
    db: Session = Depends(get_db)
):
    query = db.query(MonitoringSchedule)

    if organization_id is not None:
        query = query.filter(
            MonitoringSchedule.organization_id == organization_id
        )

    return query.order_by(
        MonitoringSchedule.created_at.desc()
    ).all()


# ENABLE MONITORING SCHEDULE

@router.patch(
    "/schedules/{monitoring_id}/enable",
    response_model=MonitoringScheduleResponse
)
def enable_monitoring_schedule(
    monitoring_id: int,
    db: Session = Depends(get_db)
):
    schedule = (
        db.query(MonitoringSchedule)
        .filter(
            MonitoringSchedule.monitoring_id == monitoring_id
        )
        .first()
    )

    if not schedule:
        raise HTTPException(
            status_code=404,
            detail="Monitoring schedule not found"
        )

    schedule.is_enabled = True
    schedule.next_run_at = (
        datetime.now(timezone.utc)
        + timedelta(hours=schedule.interval_hours)
    )
    schedule.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(schedule)

    return schedule


# DISABLE MONITORING SCHEDULE

@router.patch(
    "/schedules/{monitoring_id}/disable",
    response_model=MonitoringScheduleResponse
)
def disable_monitoring_schedule(
    monitoring_id: int,
    db: Session = Depends(get_db)
):
    schedule = (
        db.query(MonitoringSchedule)
        .filter(
            MonitoringSchedule.monitoring_id == monitoring_id
        )
        .first()
    )

    if not schedule:
        raise HTTPException(
            status_code=404,
            detail="Monitoring schedule not found"
        )

    schedule.is_enabled = False
    schedule.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(schedule)

    return schedule
