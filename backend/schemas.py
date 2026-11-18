from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field
from decimal import Decimal

class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ORGANIZATIONS

class OrganizationCreate(BaseModel):
    organization_name: str
    industry: Optional[str] = None
    organization_size: Optional[str] = None


class OrganizationResponse(ORMBase):
    organization_id: int
    organization_name: str
    industry: Optional[str] = None
    organization_size: Optional[str] = None
    created_at: Optional[datetime] = None


# ASSETS

class AssetCreate(BaseModel):
    organization_id: int
    asset_name: str
    asset_type: str = "Other"
    lab_name: Optional[str] = None
    operating_system: Optional[str] = None
    ip_address: Optional[str] = None
    criticality: str = "Medium"
    hostname: Optional[str] = None
    environment: Optional[str] = None
    owner: Optional[str] = None
    business_unit: Optional[str] = None
    cloud_provider: Optional[str] = None
    exposure_level: Optional[str] = None
    estimated_asset_value: Optional[Decimal] = Field(default=None, ge=0)
    asset_metadata: dict[str, Any] = Field(default_factory=dict)

class AssetResponse(ORMBase):
    asset_id: int
    organization_id: Optional[int] = None
    asset_name: str
    asset_type: str
    lab_name: Optional[str] = None
    operating_system: Optional[str] = None
    ip_address: Optional[str] = None
    criticality: Optional[str] = None
    hostname: Optional[str] = None
    environment: Optional[str] = None
    owner: Optional[str] = None
    business_unit: Optional[str] = None
    cloud_provider: Optional[str] = None
    exposure_level: Optional[str] = None
    estimated_asset_value: Optional[Decimal] = None
    asset_metadata: Optional[dict[str, Any]] = None
    last_seen: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# RISK FINDINGS

class RiskFindingCreate(BaseModel):
    organization_id: int
    asset_id: Optional[int] = None
    category: str
    source: str = "Manual"
    title: str
    description: Optional[str] = None
    severity: str
    likelihood: Optional[float] = None
    impact: Optional[float] = None
    evidence: dict[str, Any] = Field(default_factory=dict)


class RiskFindingResponse(ORMBase):
    finding_id: int
    organization_id: int
    asset_id: Optional[int] = None
    category: str
    source: Optional[str] = None
    title: str
    description: Optional[str] = None
    severity: str
    likelihood: Optional[float] = None
    impact: Optional[float] = None
    status: Optional[str] = None
    evidence: Optional[dict[str, Any]] = None
    detected_at: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


# SECURITY CONTROLS

class SecurityControlCreate(BaseModel):
    control_key: str
    control_name: str
    category: str
    description: Optional[str] = None
    framework: Optional[str] = None


class SecurityControlResponse(ORMBase):
    control_id: int
    control_key: str
    control_name: str
    category: str
    description: Optional[str] = None
    framework: Optional[str] = None


# CONTROL ASSESSMENTS

class ControlAssessmentCreate(BaseModel):
    organization_id: int
    asset_id: Optional[int] = None
    control_id: int
    status: str
    effectiveness_score: Optional[float] = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    next_review_at: Optional[datetime] = None


class ControlAssessmentResponse(ORMBase):
    assessment_id: int
    organization_id: int
    asset_id: Optional[int] = None
    control_id: int
    status: str
    effectiveness_score: Optional[float] = None
    evidence: Optional[dict[str, Any]] = None
    assessed_at: Optional[datetime] = None
    next_review_at: Optional[datetime] = None


# ASSET METRICS

class AssetMetricCreate(BaseModel):
    organization_id: int
    asset_id: int
    cpu_usage: Optional[float] = Field(default=None, ge=0, le=100)
    memory_usage: Optional[float] = Field(default=None, ge=0, le=100)
    disk_usage: Optional[float] = Field(default=None, ge=0, le=100)
    network_in: Optional[float] = Field(default=None, ge=0)
    network_out: Optional[float] = Field(default=None, ge=0)
    additional_metrics: dict[str, Any] = Field(default_factory=dict)


class AssetMetricResponse(ORMBase):
    metric_id: int
    organization_id: int
    asset_id: int
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    disk_usage: Optional[float] = None
    network_in: Optional[float] = None
    network_out: Optional[float] = None
    additional_metrics: Optional[dict[str, Any]] = None
    observed_at: Optional[datetime] = None


# VULNERABILITIES

class VulnerabilityCreate(BaseModel):
    cve_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    severity: str
    cvss_score: Optional[float] = Field(default=None, ge=0, le=10)


class VulnerabilityResponse(ORMBase):
    vulnerability_id: int
    cve_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    severity: str
    cvss_score: Optional[float] = None
    created_at: Optional[datetime] = None


# RISK ASSESSMENTS

class RiskAssessmentCreate(BaseModel):
    organization_id: Optional[int] = None
    asset_id: int
    risk_score: float = Field(ge=0, le=100)
    risk_level: str
    assessment_details: dict[str, Any] = Field(default_factory=dict)


class RiskAssessmentResponse(ORMBase):
    assessment_id: int
    organization_id: Optional[int] = None
    asset_id: int
    risk_score: Optional[float] = None
    risk_level: str
    assessment_details: Optional[dict[str, Any]] = None
    assessed_at: Optional[datetime] = None



# SECURITY INVESTMENTS

class SecurityInvestmentCreate(BaseModel):
    investment_name: str
    description: Optional[str] = None
    estimated_cost: float = Field(ge=0)
    estimated_risk_reduction: Optional[float] = Field(
        default=None,
        ge=0,
        le=100
    )

    # Security controls addressed by this investment
    control_ids: list[int] = Field(default_factory=list)


class SecurityInvestmentResponse(ORMBase):
    investment_id: int
    investment_name: str
    description: Optional[str] = None
    estimated_cost: float
    estimated_risk_reduction: Optional[float] = None

    # Associated security controls
    control_ids: list[int] = Field(default_factory=list)


# OPTIMIZATION

class OptimizationRunCreate(BaseModel):
    organization_id: int
    available_budget: float = Field(ge=0)

    # Leave NULL for organization-wide optimization.
    # Supply an asset ID for individual device optimization.
    asset_id: Optional[int] = None


class OptimizationRunResponse(ORMBase):
    run_id: int
    organization_id: Optional[int] = None
    asset_id: Optional[int] = None
    available_budget: float
    total_investment: Optional[float] = None
    estimated_risk_before: Optional[float] = None
    estimated_risk_after: Optional[float] = None
    created_at: Optional[datetime] = None


class OptimizationRecommendationResponse(ORMBase):
    recommendation_id: int
    run_id: int
    investment_id: int
    recommended_amount: Optional[float] = None
    expected_risk_reduction: Optional[float] = None

# ORGANIZATION-LEVEL RISK SUMMARY

class OrganizationAssetRiskItem(BaseModel):
    asset_id: int
    asset_name: str
    criticality: Optional[str] = None
    risk_score: float
    risk_level: str
    criticality_weight: int
    assessment_id: int
    assessed_at: Optional[datetime] = None


class UnassessedAssetItem(BaseModel):
    asset_id: int
    asset_name: str
    criticality: Optional[str] = None
    reason: str


class OrganizationRiskSummaryResponse(BaseModel):
    organization_id: int
    organization_name: str

    risk_score: Optional[float] = None
    risk_level: str

    total_assets: int
    assessed_assets: int
    unassessed_assets: int

    risk_distribution: dict[str, int]

    asset_risks: list[OrganizationAssetRiskItem]
    highest_risk_assets: list[OrganizationAssetRiskItem]

    unassessed_asset_details: list[UnassessedAssetItem] = Field(
        default_factory=list
    )

    methodology: str
    assessment_coverage_percentage: float
    calculation: Optional[str] = None

    
class ScanStartRequest(BaseModel):
    organization_id: int
    target_network: str


class ScanJobResponse(ORMBase):
    scan_id: int
    organization_id: int
    target_network: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None


class ScanResultResponse(ORMBase):
    result_id: int
    scan_id: int
    asset_id: Optional[int] = None
    ip_address: str
    hostname: Optional[str] = None
    port: Optional[int] = None
    protocol: Optional[str] = None
    state: Optional[str] = None
    service_name: Optional[str] = None
    product: Optional[str] = None
    version: Optional[str] = None
    extra_info: Optional[str] = None
    discovered_at: Optional[datetime] = None


# ==========================================
# CONTINUOUS MONITORING
# ==========================================

class MonitoringScheduleCreate(BaseModel):
    organization_id: int
    target_network: str
    interval_hours: int = Field(default=24, ge=1, le=720)


class MonitoringScheduleResponse(ORMBase):
    monitoring_id: int
    organization_id: int
    target_network: str
    interval_hours: int
    is_enabled: bool
    last_run_at: Optional[datetime] = None
    next_run_at: datetime
    last_scan_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ==========================================
# GLOBAL DEVICE SCAN HISTORY
# ==========================================

class DeviceScanHistoryItem(ORMBase):
    scan_id: int
    organization_id: int
    target_network: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    result_count: int = 0


class ScanDetailsResponse(BaseModel):
    scan: ScanJobResponse
    total_results: int
    results: list[ScanResultResponse]
