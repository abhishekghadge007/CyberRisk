
from sqlalchemy import (
    Column,
    BigInteger,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Boolean,
)
from sqlalchemy.sql import func
from sqlalchemy import (
    Numeric,
    TIMESTAMP,
    Index,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import INET, JSONB

from database import Base


# ==========================================
# 1. ORGANIZATIONS
# ==========================================

class Organization(Base):
    __tablename__ = "organizations"

    organization_id = Column(BigInteger, primary_key=True, autoincrement=True)
    organization_name = Column(String(200), nullable=False)
    industry = Column(String(100))
    organization_size = Column(String(50))
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"))


# ==========================================
# 2. ASSETS
# ==========================================

class Asset(Base):
    __tablename__ = "assets"

    asset_id = Column(BigInteger, primary_key=True, autoincrement=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.organization_id"))

    asset_name = Column(String(150), nullable=False)
    asset_type = Column(String(50), nullable=False, server_default=text("'PC'"))
    lab_name = Column(String(100))
    operating_system = Column(String(100))
    ip_address = Column(INET)
    criticality = Column(String(20), server_default=text("'Medium'"))
    last_seen = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    hostname = Column(String(255))
    environment = Column(String(50))
    owner = Column(String(150))
    business_unit = Column(String(150))
    cloud_provider = Column(String(100))
    exposure_level = Column(String(30))
    estimated_asset_value = Column(Numeric(15, 2), nullable=True)
    asset_metadata = Column(JSONB, server_default=text("'{}'::jsonb"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    __table_args__ = (
        Index("idx_assets_lab", "lab_name"),
        Index("idx_assets_organization", "organization_id"),
    )


# ==========================================
# 3. VULNERABILITIES
# ==========================================

class Vulnerability(Base):
    __tablename__ = "vulnerabilities"

    vulnerability_id = Column(BigInteger, primary_key=True, autoincrement=True)
    cve_id = Column(String(30), unique=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    severity = Column(String(20), nullable=False)
    cvss_score = Column(Numeric(3, 1))
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"))


# ==========================================
# 4. ASSET VULNERABILITIES
# ==========================================

class AssetVulnerability(Base):
    __tablename__ = "asset_vulnerabilities"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    asset_id = Column(BigInteger, ForeignKey("assets.asset_id", ondelete="CASCADE"))
    vulnerability_id = Column(BigInteger, ForeignKey("vulnerabilities.vulnerability_id", ondelete="CASCADE"))
    status = Column(String(30), server_default=text("'Open'"))
    detected_at = Column(TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    resolved_at = Column(TIMESTAMP(timezone=True))

    __table_args__ = (
        UniqueConstraint("asset_id", "vulnerability_id"),
        Index("idx_asset_vulnerabilities_asset", "asset_id"),
    )


# ==========================================
# 5. RISK ASSESSMENTS
# ==========================================

class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    assessment_id = Column(BigInteger, primary_key=True, autoincrement=True)
    asset_id = Column(BigInteger, ForeignKey("assets.asset_id", ondelete="CASCADE"))
    risk_score = Column(Numeric(5, 2), nullable=True)
    risk_level = Column(String(20), nullable=False)
    assessment_details = Column(JSONB)
    assessed_at = Column(TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    organization_id = Column(BigInteger, ForeignKey("organizations.organization_id"))

    __table_args__ = (
        Index("idx_risk_assessments_asset", "asset_id"),
        Index("idx_risk_assessments_date", "assessed_at"),
        Index("idx_risk_organization", "organization_id"),
    )


# ==========================================
# 6. SECURITY INVESTMENTS
# ==========================================

class SecurityInvestment(Base):
    __tablename__ = "security_investments"

    investment_id = Column(BigInteger, primary_key=True, autoincrement=True)
    investment_name = Column(String(200), nullable=False)
    description = Column(Text)
    estimated_cost = Column(Numeric(12, 2), nullable=False)
    estimated_risk_reduction = Column(Numeric(5, 2))
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"))


# ==========================================
# 6A. INVESTMENT CONTROL MAPPING
# ==========================================

class InvestmentControl(Base):
    __tablename__ = "investment_controls"

    mapping_id = Column(BigInteger, primary_key=True, autoincrement=True)

    investment_id = Column(
        BigInteger,
        ForeignKey("security_investments.investment_id", ondelete="CASCADE"),
        nullable=False
    )

    control_id = Column(
        BigInteger,
        ForeignKey("security_controls.control_id", ondelete="CASCADE"),
        nullable=False
    )

    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=text("CURRENT_TIMESTAMP")
    )

    __table_args__ = (
        UniqueConstraint(
            "investment_id",
            "control_id",
            name="uq_investment_control"
        ),
        Index("idx_investment_controls_investment", "investment_id"),
        Index("idx_investment_controls_control", "control_id"),
    )


# ==========================================
# 7. OPTIMIZATION RUNS
# ==========================================

class OptimizationRun(Base):
    __tablename__ = "optimization_runs"

    run_id = Column(BigInteger, primary_key=True, autoincrement=True)

    available_budget = Column(Numeric(12, 2), nullable=False)

    total_investment = Column(
        Numeric(12, 2),
        server_default=text("0")
    )

    estimated_risk_before = Column(Numeric(5, 2))
    estimated_risk_after = Column(Numeric(5, 2))

    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=text("CURRENT_TIMESTAMP")
    )

    organization_id = Column(
        BigInteger,
        ForeignKey("organizations.organization_id")
    )

    # NULL means organization-wide or multi-asset optimization.
    asset_id = Column(
        BigInteger,
        ForeignKey("assets.asset_id", ondelete="SET NULL"),
        nullable=True
    )

    __table_args__ = (
        Index("idx_optimization_runs_organization", "organization_id"),
        Index("idx_optimization_runs_asset", "asset_id"),
    )


# ==========================================
# 7A. MULTI-ASSET OPTIMIZATION RUN ASSETS
# ==========================================

class OptimizationRunAsset(Base):
    __tablename__ = "optimization_run_assets"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    run_id = Column(
        BigInteger,
        ForeignKey("optimization_runs.run_id", ondelete="CASCADE"),
        nullable=False
    )

    asset_id = Column(
        BigInteger,
        ForeignKey("assets.asset_id", ondelete="CASCADE"),
        nullable=False
    )

    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=text("CURRENT_TIMESTAMP")
    )

    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "asset_id",
            name="uq_optimization_run_asset"
        ),
        Index("idx_optimization_run_assets_run", "run_id"),
        Index("idx_optimization_run_assets_asset", "asset_id"),
    )


# ==========================================
# 8. OPTIMIZATION RECOMMENDATIONS
# ==========================================

class OptimizationRecommendation(Base):
    __tablename__ = "optimization_recommendations"

    recommendation_id = Column(BigInteger, primary_key=True, autoincrement=True)

    run_id = Column(
        BigInteger,
        ForeignKey("optimization_runs.run_id", ondelete="CASCADE")
    )

    investment_id = Column(
        BigInteger,
        ForeignKey("security_investments.investment_id")
    )

    recommended_amount = Column(Numeric(12, 2))
    expected_risk_reduction = Column(Numeric(5, 2))

    # NEW: Asset receiving this recommendation.
    # NULL remains valid for existing organization-wide recommendations.
    asset_id = Column(
        BigInteger,
        ForeignKey("assets.asset_id", ondelete="SET NULL"),
        nullable=True
    )

    # NEW: Explainable optimization priority.
    priority_weight = Column(
        Numeric(5, 2),
        nullable=True
    )

    __table_args__ = (
        Index("idx_optimization_recommendations_asset", "asset_id"),
        Index("idx_optimization_recommendations_run", "run_id"),
    )


# ==========================================
# 9. RISK FINDINGS
# ==========================================

class RiskFinding(Base):
    __tablename__ = "risk_findings"

    finding_id = Column(BigInteger, primary_key=True, autoincrement=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.organization_id", ondelete="CASCADE"), nullable=False)
    asset_id = Column(BigInteger, ForeignKey("assets.asset_id", ondelete="SET NULL"))

    category = Column(String(60), nullable=False)
    source = Column(String(60), server_default=text("'Manual'"))
    title = Column(String(255), nullable=False)
    description = Column(Text)
    severity = Column(String(20), nullable=False)

    likelihood = Column(Numeric(5, 2))
    impact = Column(Numeric(5, 2))
    status = Column(String(30), server_default=text("'Open'"))
    evidence = Column(JSONB, server_default=text("'{}'::jsonb"))

    detected_at = Column(TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    last_seen = Column(TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    resolved_at = Column(TIMESTAMP(timezone=True))

    __table_args__ = (
        Index("idx_findings_organization", "organization_id"),
        Index("idx_findings_asset", "asset_id"),
        Index("idx_findings_severity", "severity"),
    )


# ==========================================
# 10. SECURITY CONTROLS
# ==========================================

class SecurityControl(Base):
    __tablename__ = "security_controls"

    control_id = Column(BigInteger, primary_key=True, autoincrement=True)
    control_key = Column(String(100), unique=True, nullable=False)
    control_name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)
    description = Column(Text)
    framework = Column(String(100))
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"))


# ==========================================
# 11. CONTROL ASSESSMENTS
# ==========================================

class ControlAssessment(Base):
    __tablename__ = "control_assessments"

    assessment_id = Column(BigInteger, primary_key=True, autoincrement=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.organization_id", ondelete="CASCADE"), nullable=False)
    asset_id = Column(BigInteger, ForeignKey("assets.asset_id", ondelete="SET NULL"))
    control_id = Column(BigInteger, ForeignKey("security_controls.control_id"), nullable=False)

    status = Column(String(30), nullable=False)
    effectiveness_score = Column(Numeric(5, 2))
    evidence = Column(JSONB, server_default=text("'{}'::jsonb"))

    assessed_at = Column(TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    next_review_at = Column(TIMESTAMP(timezone=True))

    __table_args__ = (
        Index("idx_controls_organization", "organization_id"),
    )


# ==========================================
# 12. ASSET METRICS
# ==========================================

class AssetMetric(Base):
    __tablename__ = "asset_metrics"

    metric_id = Column(BigInteger, primary_key=True, autoincrement=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.organization_id", ondelete="CASCADE"), nullable=False)
    asset_id = Column(BigInteger, ForeignKey("assets.asset_id", ondelete="CASCADE"), nullable=False)

    cpu_usage = Column(Numeric(6, 2))
    memory_usage = Column(Numeric(6, 2))
    disk_usage = Column(Numeric(6, 2))

    network_in = Column(Numeric(14, 2))
    network_out = Column(Numeric(14, 2))

    additional_metrics = Column(JSONB, server_default=text("'{}'::jsonb"))
    observed_at = Column(TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    __table_args__ = (
        Index("idx_metrics_asset", "asset_id"),
        Index("idx_metrics_observed", "observed_at"),
    )


# ==========================================
# NETWORK SCANNING MODELS
# ==========================================

class ScanJob(Base):
    __tablename__ = "scan_jobs"

    scan_id = Column(BigInteger, primary_key=True, index=True)

    organization_id = Column(
        BigInteger,
        ForeignKey("organizations.organization_id", ondelete="CASCADE"),
        nullable=False
    )

    target_network = Column(String(64), nullable=False)

    status = Column(
        String(20),
        nullable=False,
        default="queued"
    )

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


class ScanResult(Base):
    __tablename__ = "scan_results"

    result_id = Column(BigInteger, primary_key=True, index=True)

    scan_id = Column(
        BigInteger,
        ForeignKey("scan_jobs.scan_id", ondelete="CASCADE"),
        nullable=False
    )

    asset_id = Column(
        BigInteger,
        ForeignKey("assets.asset_id", ondelete="SET NULL"),
        nullable=True
    )

    ip_address = Column(String(45), nullable=False)
    hostname = Column(String(255), nullable=True)

    port = Column(Integer, nullable=True)
    protocol = Column(String(10), nullable=True)
    state = Column(String(30), nullable=True)

    service_name = Column(String(100), nullable=True)
    product = Column(String(255), nullable=True)
    version = Column(String(255), nullable=True)
    extra_info = Column(Text, nullable=True)

    discovered_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


# ==========================================
# 13. CONTINUOUS MONITORING SCHEDULES
# ==========================================

class MonitoringSchedule(Base):
    __tablename__ = "monitoring_schedules"

    monitoring_id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )

    organization_id = Column(
        BigInteger,
        ForeignKey("organizations.organization_id", ondelete="CASCADE"),
        nullable=False
    )

    target_network = Column(String(64), nullable=False)

    interval_hours = Column(
        Integer,
        nullable=False,
        default=24
    )

    is_enabled = Column(
        Boolean,
        nullable=False,
        default=True
    )

    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=False)

    last_scan_id = Column(
        BigInteger,
        ForeignKey("scan_jobs.scan_id", ondelete="SET NULL"),
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "target_network",
            name="uq_monitoring_organization_network"
        ),
        Index("idx_monitoring_due", "is_enabled", "next_run_at"),
    )


# ==========================================
# API ACTIVITY LOG
# ==========================================

class APIActivityLog(Base):
    __tablename__ = "api_activity_logs"

    log_id = Column(BigInteger, primary_key=True, index=True)
    endpoint = Column(String(500), nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=False)
    source = Column(String(30), nullable=False, default="Other")
    response_time_ms = Column(Integer, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
