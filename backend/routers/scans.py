
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import Organization, ScanJob, ScanResult
from schemas import (
    ScanStartRequest,
    ScanJobResponse,
    ScanResultResponse,
    ScanDetailsResponse
)

from services.nmap_service import (
    execute_nmap_scan,
    validate_target
)

from services.vulnerability_service import (
    analyze_scan_vulnerabilities
)


router = APIRouter(
    prefix="/api/scans",
    tags=["Network Scanning"]
)


# ==========================================
# START NETWORK SCAN
# ==========================================

@router.post("/start", response_model=ScanJobResponse, status_code=202)
def start_scan(
    request: ScanStartRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    organization = db.query(Organization).filter(
        Organization.organization_id == request.organization_id
    ).first()

    if not organization:
        raise HTTPException(
            status_code=404,
            detail="Organization not found"
        )

    try:
        target = validate_target(request.target_network)
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    scan = ScanJob(
        organization_id=request.organization_id,
        target_network=target,
        status="queued"
    )

    db.add(scan)
    db.commit()
    db.refresh(scan)

    background_tasks.add_task(
        execute_nmap_scan,
        scan.scan_id
    )

    return scan


# ==========================================
# GLOBAL SCAN HISTORY
# ==========================================

@router.get("/", response_model=list[ScanJobResponse])
def get_global_scan_history(
    organization_id: int = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    if limit < 1 or limit > 500:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 500"
        )

    if offset < 0:
        raise HTTPException(
            status_code=400,
            detail="Offset cannot be negative"
        )

    query = db.query(ScanJob)

    if organization_id is not None:
        query = query.filter(
            ScanJob.organization_id == organization_id
        )

    return query.order_by(
        ScanJob.created_at.desc()
    ).offset(offset).limit(limit).all()


# ==========================================
# GET SCAN DETAILS
# ==========================================

@router.get("/{scan_id}/details", response_model=ScanDetailsResponse)
def get_scan_details(
    scan_id: int,
    db: Session = Depends(get_db)
):
    scan = db.query(ScanJob).filter(
        ScanJob.scan_id == scan_id
    ).first()

    if not scan:
        raise HTTPException(
            status_code=404,
            detail="Scan not found"
        )

    results = db.query(ScanResult).filter(
        ScanResult.scan_id == scan_id
    ).order_by(
        ScanResult.ip_address,
        ScanResult.port
    ).all()

    return {
        "scan": scan,
        "total_results": len(results),
        "results": results
    }


# ==========================================
# CHECK SCAN STATUS
# ==========================================

@router.get("/{scan_id}", response_model=ScanJobResponse)
def get_scan_status(
    scan_id: int,
    db: Session = Depends(get_db)
):
    scan = db.query(ScanJob).filter(
        ScanJob.scan_id == scan_id
    ).first()

    if not scan:
        raise HTTPException(
            status_code=404,
            detail="Scan not found"
        )

    return scan


# ==========================================
# GET SCAN RESULTS
# ==========================================

@router.get(
    "/{scan_id}/results",
    response_model=list[ScanResultResponse]
)
def get_scan_results(
    scan_id: int,
    db: Session = Depends(get_db)
):
    scan = db.query(ScanJob).filter(
        ScanJob.scan_id == scan_id
    ).first()

    if not scan:
        raise HTTPException(
            status_code=404,
            detail="Scan not found"
        )

    return db.query(ScanResult).filter(
        ScanResult.scan_id == scan_id
    ).order_by(
        ScanResult.ip_address,
        ScanResult.port
    ).all()


# ==========================================
# ANALYZE SCAN VULNERABILITIES
# ==========================================

@router.post("/{scan_id}/analyze-vulnerabilities")
def analyze_vulnerabilities(
    scan_id: int,
    db: Session = Depends(get_db)
):
    try:
        return analyze_scan_vulnerabilities(db, scan_id)

    except ValueError as error:
        status_code = (
            404 if "not found" in str(error).lower()
            else 400
        )

        raise HTTPException(
            status_code=status_code,
            detail=str(error)
        )

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Vulnerability analysis failed: {str(error)[:300]}"
        )
