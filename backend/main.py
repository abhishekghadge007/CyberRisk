import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import SessionLocal
from models import APIActivityLog

from routers import organizations
from routers import assets
from routers import risk_findings
from routers import risk_assessments
from routers import organization_risk
from routers import security_investments
from routers import optimization
from routers import scans
from routers import monitoring
from routers import asset_metrics
from routers import anomaly_detection
from routers import api_activity
from routers import wazuh

from routers.security_controls import router as security_controls_router
from routers.control_assessments import router as control_assessments_router
from routers.security_posture import router as security_posture_router
from routers.asset_security_posture import router as asset_security_posture_router
from routers.openvas import router as openvas_router

from services.monitoring_service import (
    start_scheduler,
    stop_scheduler,
    scheduler
)


# ==========================================
# APPLICATION LIFESPAN
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    # Start continuous monitoring
    start_scheduler()

    yield

    # Stop continuous monitoring during shutdown
    stop_scheduler()


# ==========================================
# FASTAPI APPLICATION
# ==========================================

app = FastAPI(
    title="CyberRisk Optimizer",
    description=(
        "AI-Powered Continuous Cyber Risk Quantification "
        "and Investment Optimization Platform"
    ),
    version="1.0.0",
    lifespan=lifespan
)


# ==========================================
# API ACTIVITY TRACKING MIDDLEWARE
# ==========================================

@app.middleware("http")
async def track_api_activity(request, call_next):

    request_path = request.url.path

    # Track API endpoints only
    if not request_path.startswith("/api/"):
        return await call_next(request)

    # Ignore browser preflight requests
    if request.method == "OPTIONS":
        return await call_next(request)

    # Do not count API activity dashboard requests
    if request_path.startswith("/api/api-activity/"):
        return await call_next(request)

    start_time = time.perf_counter()

    status_code = 500

    try:
        response = await call_next(request)

        status_code = response.status_code

        return response

    finally:

        response_time = int(
            (time.perf_counter() - start_time) * 1000
        )

        # Identify request source
        referer = request.headers.get("referer", "")

        if "/docs" in referer:
            source = "Swagger UI"

        elif "/redoc" in referer:
            source = "ReDoc"

        else:
            source = "Other"

        db = SessionLocal()

        try:

            activity = APIActivityLog(
                endpoint=request_path,
                method=request.method,
                status_code=status_code,
                source=source,
                response_time_ms=response_time
            )

            db.add(activity)
            db.commit()

        except Exception as error:

            db.rollback()

            print(
                "API activity logging failed:",
                error
            )

        finally:

            db.close()


# ==========================================
# REGISTER API ROUTERS
# ==========================================

app.include_router(organizations.router)
app.include_router(assets.router)
app.include_router(risk_findings.router)
app.include_router(risk_assessments.router)
app.include_router(organization_risk.router)
app.include_router(security_investments.router)
app.include_router(optimization.router)
app.include_router(scans.router)
app.include_router(monitoring.router)
app.include_router(asset_metrics.router)
app.include_router(anomaly_detection.router)
app.include_router(wazuh.router)

# API activity tracking endpoints
app.include_router(api_activity.router)

# Security controls
app.include_router(security_controls_router)
app.include_router(control_assessments_router)
app.include_router(security_posture_router)
app.include_router(asset_security_posture_router)
app.include_router(openvas_router)

# ==========================================
# CORS CONFIGURATION
# ==========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# HOME ENDPOINT
# ==========================================

@app.get("/")
def home():

    return {
        "message": "Welcome to CyberRisk API",
        "status": "Running",
        "version": "1.0.0"
    }


# ==========================================
# HEALTH CHECK
# ==========================================

@app.get("/api/health")
def health_check():

    return {
        "status": "healthy",
        "application": "CyberRisk",
        "backend": "FastAPI"
    }


# ==========================================
# DASHBOARD
# ==========================================

@app.get("/api/dashboard")
def dashboard():

    return {
        "overall_risk_score": 42,
        "monitored_assets": 128,
        "open_vulnerabilities": 30,
        "security_controls": 84,
        "message": "Dashboard API is working"
    }


# ==========================================
# MONITORING SCHEDULER STATUS
# ==========================================

@app.get("/api/monitoring/scheduler-status")
def monitoring_scheduler_status():

    return {
        "scheduler_running": scheduler.running,
        "scheduled_jobs": [
            {
                "job_id": job.id,
                "next_run_time": str(job.next_run_time)
            }
            for job in scheduler.get_jobs()
        ]
    }
