from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db

from models import (
    Asset,
    RiskAssessment,
    OptimizationRun,
    OptimizationRecommendation,
    InvestmentControl,
    SecurityInvestment,
)

from schemas import OptimizationRunCreate

from services.control_gap_engine import (
    get_verified_control_gaps,
)

from services.organization_risk_engine import (
    calculate_organization_risk,
)

from services.organization_predictive_engine import (
    analyze_organization_history,
)

from services.optimization_engine import (
    optimize_security_investments,
)


router = APIRouter(
    prefix="/api/optimization",
    tags=["Investment Optimization"],
)


# ==========================================
# BUILD PREDICTIVE INVESTMENT PRIORITIES
# ==========================================

def build_investment_priorities(
    investments,
    verified_gaps,
    predictive_analysis,
    investment_control_rows,
):
    """
    Assign additional investment priority using predictive signals.

    A predictive signal is associated with a verified control gap
    only when both refer to the same asset.
    """

    risk_weights = {
        "Critical": 3.0,
        "High": 2.0,
        "Moderate": 1.5,
        "Medium": 1.5,
        "Low": 1.25,
    }

    signals_by_asset = {}

    for signal in predictive_analysis.get(
        "emerging_risk_signals", []
    ):
        asset_id = signal.get("asset_id")

        if asset_id is not None:
            signals_by_asset[asset_id] = signal

    gaps_by_asset = {}

    for gap in verified_gaps:
        asset_id = gap.get("asset_id")
        control_id = gap.get("control_id")

        if asset_id is None or control_id is None:
            continue

        gaps_by_asset.setdefault(
            asset_id, set()
        ).add(control_id)

    controls_by_investment = {}

    for mapping in investment_control_rows:
        controls_by_investment.setdefault(
            mapping.investment_id, set()
        ).add(mapping.control_id)

    investment_priorities = {}

    for investment in investments:

        investment_id = investment.investment_id

        mapped_control_ids = controls_by_investment.get(
            investment_id, set()
        )

        priority_weight = 1.0

        matched_asset_ids = set()
        matched_control_ids = set()
        priority_reasons = []

        for asset_id, gap_control_ids in gaps_by_asset.items():

            if asset_id not in signals_by_asset:
                continue

            matching_controls = (
                mapped_control_ids.intersection(
                    gap_control_ids
                )
            )

            if not matching_controls:
                continue

            signal = signals_by_asset[asset_id]

            matched_asset_ids.add(asset_id)
            matched_control_ids.update(matching_controls)

            finding_risk_level = signal.get(
                "finding_risk_level"
            )

            historical_trend = signal.get(
                "historical_trend"
            )

            operational_anomalies = signal.get(
                "open_operational_anomalies", 0
            ) or 0

            risk_weight = risk_weights.get(
                finding_risk_level, 1.0
            )

            priority_weight = max(
                priority_weight,
                risk_weight
            )

            asset_name = signal.get(
                "asset_name",
                f"Asset {asset_id}"
            )

            for control_id in sorted(matching_controls):
                priority_reasons.append(
                    f"Verified control gap for control "
                    f"{control_id} exists on {asset_name}, "
                    f"which has {finding_risk_level or 'unknown'} "
                    f"predictive finding risk."
                )

            if operational_anomalies > 0:

                priority_weight = max(
                    priority_weight, 1.5
                )

                priority_reasons.append(
                    f"{asset_name} has "
                    f"{operational_anomalies} open "
                    f"operational anomaly/anomalies."
                )

            if historical_trend == "Increasing":

                priority_weight = max(
                    priority_weight, 1.25
                )

                priority_reasons.append(
                    f"{asset_name} has an increasing "
                    f"historical risk trend."
                )

        investment_priorities[investment_id] = {
            "priority_weight": min(
                priority_weight, 3.0
            ),
            "priority_reasons": list(
                dict.fromkeys(priority_reasons)
            ) or [
                "No asset-level predictive match. "
                "Standard investment priority applied."
            ],
            "matched_asset_ids": sorted(
                matched_asset_ids
            ),
            "matched_control_ids": sorted(
                matched_control_ids
            ),
        }

    return investment_priorities


# ==========================================
# RUN INVESTMENT OPTIMIZATION
# ==========================================

@router.post(
    "/run",
    status_code=status.HTTP_201_CREATED,
)
def run_optimization(
    request: OptimizationRunCreate,
    db: Session = Depends(get_db),
):

    organization_id = request.organization_id
    asset_id = request.asset_id

    if organization_id is None:
        raise HTTPException(
            status_code=400,
            detail="Organization ID is required.",
        )

    # ==========================================
    # 1. VALIDATE SELECTED ORGANIZATION
    # ==========================================

    selected_asset = None

    if asset_id is not None:

        selected_asset = (
            db.query(Asset)
            .filter(
                Asset.asset_id == asset_id,
                Asset.organization_id == organization_id,
            )
            .first()
        )

        if not selected_asset:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Selected asset was not found in the "
                    "specified organization."
                ),
            )

    # ==========================================
    # 2. CALCULATE BASELINE RISK
    # ==========================================

    if asset_id is None:

        # Organization-wide optimization.
        try:
            risk_summary = calculate_organization_risk(
                db,
                organization_id,
            )

        except ValueError as error:
            raise HTTPException(
                status_code=404,
                detail=str(error),
            )

        baseline_risk = risk_summary["risk_score"]

        organization_risk_level = risk_summary["risk_level"]

        if baseline_risk is None:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Organization has no assessed assets. "
                    "Calculate asset risk first."
                ),
            )

        optimization_scope = "Organization-wide"

    else:

        # Individual-device optimization.
        latest_assessment = (
            db.query(RiskAssessment)
            .filter(
                RiskAssessment.organization_id == organization_id,
                RiskAssessment.asset_id == asset_id,
                RiskAssessment.risk_score.isnot(None),
            )
            .order_by(
                RiskAssessment.assessed_at.desc(),
                RiskAssessment.assessment_id.desc(),
            )
            .first()
        )

        if not latest_assessment:
            raise HTTPException(
                status_code=422,
                detail=(
                    "The selected device has no valid risk "
                    "assessment. Calculate its risk before "
                    "running investment optimization."
                ),
            )

        baseline_risk = float(
            latest_assessment.risk_score
        )

        organization_risk_level = (
            latest_assessment.risk_level
        )

        risk_summary = {
            "risk_score": baseline_risk,
            "risk_level": organization_risk_level,
        }

        optimization_scope = "Individual device"

    # ==========================================
    # 3. IDENTIFY VERIFIED SECURITY-CONTROL GAPS
    # ==========================================

    verified_gaps = get_verified_control_gaps(
        db,
        organization_id,
    )

    # Restrict gaps to the selected device when
    # individual-device optimization is requested.

    if asset_id is not None:
        verified_gaps = [
            gap
            for gap in verified_gaps
            if gap.get("asset_id") == asset_id
        ]

    if not verified_gaps:
        raise HTTPException(
            status_code=422,
            detail=(
                "No verified security-control gaps were found "
                "for the selected optimization scope. Verify "
                "the relevant control assessments first."
            ),
        )

    gap_control_ids = sorted({
        gap["control_id"]
        for gap in verified_gaps
        if gap.get("control_id") is not None
    })

    if not gap_control_ids:
        raise HTTPException(
            status_code=422,
            detail=(
                "Verified gaps were found, but none contain "
                "a valid control ID."
            ),
        )

    # ==========================================
    # 4. FIND INVESTMENTS ADDRESSING THOSE GAPS
    # ==========================================

    eligible_investment_rows = (
        db.query(InvestmentControl.investment_id)
        .filter(
            InvestmentControl.control_id.in_(
                gap_control_ids
            )
        )
        .distinct()
        .all()
    )

    eligible_investment_ids = [
        row.investment_id
        for row in eligible_investment_rows
    ]

    if not eligible_investment_ids:
        raise HTTPException(
            status_code=422,
            detail=(
                "Verified security-control gaps exist, but no "
                "investments are mapped to those controls. "
                "Map relevant investments before optimization."
            ),
        )

    investments = (
        db.query(SecurityInvestment)
        .filter(
            SecurityInvestment.investment_id.in_(
                eligible_investment_ids
            )
        )
        .order_by(
            SecurityInvestment.investment_id.asc()
        )
        .all()
    )

    if not investments:
        raise HTTPException(
            status_code=422,
            detail="No eligible security investments were found.",
        )

    # ==========================================
    # 5. GENERATE PREDICTIVE ANALYSIS
    # ==========================================

    try:
        predictive_analysis = analyze_organization_history(
            db,
            organization_id,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=(
                "Predictive analysis could not be generated: "
                + str(error)
            ),
        )

    # Restrict predictive signals to the selected device.
    # The predictive engine remains organization-level;
    # only the selected device's signals influence this run.

    if asset_id is not None:

        predictive_analysis = dict(predictive_analysis)

        predictive_analysis["emerging_risk_signals"] = [
            signal
            for signal in predictive_analysis.get(
                "emerging_risk_signals", []
            )
            if signal.get("asset_id") == asset_id
        ]

    # ==========================================
    # 6. RETRIEVE INVESTMENT-CONTROL MAPPINGS
    # ==========================================

    investment_control_rows = (
        db.query(InvestmentControl)
        .filter(
            InvestmentControl.investment_id.in_(
                eligible_investment_ids
            )
        )
        .all()
    )

    # ==========================================
    # 7. BUILD PREDICTIVE PRIORITIES
    # ==========================================

    investment_priorities = build_investment_priorities(
        investments=investments,
        verified_gaps=verified_gaps,
        predictive_analysis=predictive_analysis,
        investment_control_rows=investment_control_rows,
    )

    prioritized_investment_count = sum(
        1
        for priority in investment_priorities.values()
        if priority["priority_weight"] > 1.0
    )

    matched_investment_count = sum(
        1
        for priority in investment_priorities.values()
        if priority["matched_asset_ids"]
    )

    # ==========================================
    # 8. RUN OR-TOOLS OPTIMIZATION
    # ==========================================

    try:
        result = optimize_security_investments(
            investments=investments,
            available_budget=request.available_budget,
            baseline_risk=baseline_risk,
            investment_priorities=investment_priorities,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        )

    # ==========================================
    # 9. SAVE OPTIMIZATION RUN
    # ==========================================

    optimization_run = OptimizationRun(
        organization_id=organization_id,
        asset_id=asset_id,
        available_budget=request.available_budget,
        total_investment=result["total_investment"],
        estimated_risk_before=result["estimated_risk_before"],
        estimated_risk_after=result["estimated_risk_after"],
    )

    try:
        db.add(optimization_run)
        db.flush()

        for item in result["selected_investments"]:

            recommendation = OptimizationRecommendation(
                run_id=optimization_run.run_id,
                investment_id=item["investment_id"],
                recommended_amount=item["recommended_amount"],
                expected_risk_reduction=(
                    item["expected_risk_reduction"]
                ),
            )

            db.add(recommendation)

        db.commit()
        db.refresh(optimization_run)

    except Exception:
        db.rollback()
        raise

    # ==========================================
    # 10. RETURN OPTIMIZATION RESULTS
    # ==========================================

    return {
        "message": (
            "Predictive-priority investment optimization "
            "completed successfully."
        ),

        "run_id": optimization_run.run_id,

        "organization_id": organization_id,

        "asset_id": asset_id,

        "asset_name": (
            selected_asset.asset_name
            if selected_asset
            else None
        ),

        "optimization_scope": optimization_scope,

        "organization_risk_level": organization_risk_level,

        "solver_status": result["solver_status"],

        "available_budget": result["available_budget"],

        "total_investment": result["total_investment"],

        "remaining_budget": result["remaining_budget"],

        "estimated_risk_before": (
            result["estimated_risk_before"]
        ),

        "estimated_risk_reduction": (
            result["estimated_risk_reduction"]
        ),

        "estimated_risk_after": (
            result["estimated_risk_after"]
        ),

        "selected_investments": (
            result["selected_investments"]
        ),

        "verified_control_gaps": verified_gaps,

        "eligible_control_ids": gap_control_ids,

        "predictive_prioritization": {
            "enabled": True,

            "optimization_scope": optimization_scope,

            "organization_outlook": (
                predictive_analysis.get(
                    "organization_outlook"
                )
            ),

            "historical_trend": (
                predictive_analysis.get(
                    "historical_trend"
                )
            ),

            "current_risk_posture": (
                predictive_analysis.get(
                    "current_risk_posture"
                )
            ),

            "emerging_risk_status": (
                predictive_analysis.get(
                    "emerging_risk_status"
                )
            ),

            "data_sufficiency": (
                predictive_analysis.get(
                    "data_sufficiency"
                )
            ),

            "eligible_investments": len(investments),

            "investments_with_asset_level_matches": (
                matched_investment_count
            ),

            "investments_receiving_extra_priority": (
                prioritized_investment_count
            ),

            "matching_method": (
                "An investment receives predictive priority "
                "when its mapped control has a verified gap "
                "on the same asset that has an emerging "
                "predictive risk signal."
            ),

            "association_limitation": (
                "Same-asset association provides contextual "
                "prioritization. It does not prove that a "
                "mapped security control directly mitigates "
                "a particular risk finding."
            ),
        },

        "methodology": result["methodology"],

        "optimization_objective": (
            result["optimization_objective"]
        ),

        "constraints": result["constraints"],

        "risk_reduction_assumption": (
            "Investment risk reductions are treated as "
            "independent and additive estimates, capped at "
            "the baseline risk. Predictive priority weights "
            "influence investment selection but do not "
            "increase reported risk reduction. These are "
            "estimated improvements, not guaranteed "
            "reductions in actual risk."
        ),
    }


# ==========================================
# GET OPTIMIZATION RUN BY ID
# ==========================================

@router.get("/runs/{run_id}")
def get_optimization_run(
    run_id: int,
    db: Session = Depends(get_db),
):

    run = (
        db.query(OptimizationRun)
        .filter(
            OptimizationRun.run_id == run_id
        )
        .first()
    )

    if not run:
        raise HTTPException(
            status_code=404,
            detail="Optimization run not found.",
        )

    recommendations = (
        db.query(OptimizationRecommendation)
        .filter(
            OptimizationRecommendation.run_id == run_id
        )
        .all()
    )

    asset_name = None

    if run.asset_id is not None:
        asset = (
            db.query(Asset)
            .filter(Asset.asset_id == run.asset_id)
            .first()
        )

        if asset:
            asset_name = asset.asset_name

    return {
        "run_id": run.run_id,
        "organization_id": run.organization_id,
        "asset_id": run.asset_id,
        "asset_name": asset_name,
        "optimization_scope": (
            "Individual device"
            if run.asset_id is not None
            else "Organization-wide"
        ),

        "available_budget": float(run.available_budget),
        "total_investment": float(run.total_investment or 0),

        "estimated_risk_before": (
            float(run.estimated_risk_before)
            if run.estimated_risk_before is not None
            else None
        ),

        "estimated_risk_after": (
            float(run.estimated_risk_after)
            if run.estimated_risk_after is not None
            else None
        ),

        "created_at": run.created_at,

        "recommendations": [
            {
                "recommendation_id": item.recommendation_id,
                "investment_id": item.investment_id,

                "recommended_amount": (
                    float(item.recommended_amount)
                    if item.recommended_amount is not None
                    else None
                ),

                "expected_risk_reduction": (
                    float(item.expected_risk_reduction)
                    if item.expected_risk_reduction is not None
                    else None
                ),
            }
            for item in recommendations
        ],
    }


# ==========================================
# OPTIMIZATION HISTORY API
# ==========================================

@router.get("/history/{organization_id}")
def get_optimization_history(
    organization_id: int,
    db: Session = Depends(get_db),
):

    runs = (
        db.query(OptimizationRun)
        .filter(
            OptimizationRun.organization_id == organization_id
        )
        .order_by(
            OptimizationRun.created_at.desc()
        )
        .all()
    )

    history = []

    for run in runs:

        risk_before = (
            float(run.estimated_risk_before)
            if run.estimated_risk_before is not None
            else None
        )

        risk_after = (
            float(run.estimated_risk_after)
            if run.estimated_risk_after is not None
            else None
        )

        risk_reduction = (
            round(risk_before - risk_after, 2)
            if risk_before is not None and risk_after is not None
            else None
        )

        asset_name = None

        if run.asset_id is not None:
            asset = (
                db.query(Asset)
                .filter(Asset.asset_id == run.asset_id)
                .first()
            )

            if asset:
                asset_name = asset.asset_name

        history.append({
            "run_id": run.run_id,
            "asset_id": run.asset_id,
            "asset_name": asset_name,

            "optimization_scope": (
                "Individual device"
                if run.asset_id is not None
                else "Organization-wide"
            ),

            "available_budget": float(run.available_budget),
            "total_investment": float(run.total_investment or 0),
            "estimated_risk_before": risk_before,
            "estimated_risk_after": risk_after,
            "risk_reduction": risk_reduction,
            "created_at": run.created_at,
        })

    return {
        "organization_id": organization_id,
        "total_runs": len(history),
        "history": history,
    }


# ==========================================
# RECOMMENDATION RETRIEVAL API
# ==========================================

@router.get("/recommendations/{run_id}")
def get_optimization_recommendations(
    run_id: int,
    db: Session = Depends(get_db),
):

    run = (
        db.query(OptimizationRun)
        .filter(
            OptimizationRun.run_id == run_id
        )
        .first()
    )

    if not run:
        raise HTTPException(
            status_code=404,
            detail="Optimization run not found.",
        )

    recommendations = (
        db.query(
            OptimizationRecommendation,
            SecurityInvestment,
        )
        .join(
            SecurityInvestment,
            OptimizationRecommendation.investment_id
            == SecurityInvestment.investment_id,
        )
        .filter(
            OptimizationRecommendation.run_id == run_id
        )
        .all()
    )

    result = []

    for recommendation, investment in recommendations:

        result.append({
            "recommendation_id": recommendation.recommendation_id,
            "investment_id": investment.investment_id,
            "investment_name": investment.investment_name,
            "description": investment.description,

            "recommended_amount": float(
                recommendation.recommended_amount or 0
            ),

            "estimated_cost": float(
                investment.estimated_cost
            ),

            "expected_risk_reduction": float(
                recommendation.expected_risk_reduction or 0
            ),
        })

    return {
        "run_id": run_id,
        "organization_id": run.organization_id,
        "asset_id": run.asset_id,
        "optimization_scope": (
            "Individual device"
            if run.asset_id is not None
            else "Organization-wide"
        ),
        "total_recommendations": len(result),
        "recommendations": result,
    }
