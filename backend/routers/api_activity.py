
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import APIActivityLog

router = APIRouter(
    prefix="/api/api-activity",
    tags=["API Activity"]
)


@router.get("/summary")
def get_api_activity_summary(
    source: str = Query(default="Swagger UI"),
    db: Session = Depends(get_db)
):
    query = db.query(APIActivityLog).filter(
        APIActivityLog.source == source
    )

    total_requests = query.count()

    successful_requests = query.filter(
        APIActivityLog.status_code >= 200,
        APIActivityLog.status_code < 400
    ).count()

    failed_requests = query.filter(
        APIActivityLog.status_code >= 400
    ).count()

    unique_endpoints = query.with_entities(
        func.count(func.distinct(APIActivityLog.endpoint))
    ).scalar() or 0

    return {
        "source": source,
        "total_requests": total_requests,
        "unique_endpoints": unique_endpoints,
        "successful_requests": successful_requests,
        "failed_requests": failed_requests
    }


@router.get("/logs")
def get_api_activity_logs(
    source: str = Query(default="Swagger UI"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    logs = db.query(APIActivityLog).filter(
        APIActivityLog.source == source
    ).order_by(
        APIActivityLog.created_at.desc()
    ).limit(limit).all()

    return [
        {
            "log_id": log.log_id,
            "endpoint": log.endpoint,
            "method": log.method,
            "status_code": log.status_code,
            "source": log.source,
            "response_time_ms": log.response_time_ms,
            "created_at": log.created_at
        }
        for log in logs
    ]
