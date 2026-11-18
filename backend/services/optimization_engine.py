from decimal import Decimal, ROUND_HALF_UP

from ortools.sat.python import cp_model


def to_scaled_integer(value, scale=100):
    """
    Convert decimal values into integers for OR-Tools.
    CP-SAT works with integer coefficients.
    """
    decimal_value = Decimal(str(value))

    return int(
        (decimal_value * scale).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP
        )
    )


def optimize_security_investments(
    investments,
    available_budget: float,
    baseline_risk: float,
    investment_priorities=None,
):
    """
    Select security investments within the available budget.

    The optimizer maximizes predictive-priority-weighted
    estimated risk reduction.

    Actual estimated risk reduction remains unchanged.
    Priority weights influence selection, not the reported
    risk reduction.

    Each investment is either selected completely or rejected.
    """

    if available_budget < 0:
        raise ValueError("Available budget cannot be negative.")

    if not 0 <= baseline_risk <= 100:
        raise ValueError("Baseline risk must be between 0 and 100.")

    if not investments:
        raise ValueError("No security investments are available.")

    if investment_priorities is None:
        investment_priorities = {}

    budget_cents = to_scaled_integer(available_budget)
    baseline_risk_units = to_scaled_integer(baseline_risk)

    # Prepare valid investment options.
    valid_investments = []

    for investment in investments:

        cost = Decimal(str(investment.estimated_cost))

        reduction_value = investment.estimated_risk_reduction

        if reduction_value is None:
            continue

        reduction = Decimal(str(reduction_value))

        if cost < 0 or reduction <= 0:
            continue

        # Read optional predictive priority information.
        priority_info = investment_priorities.get(
            investment.investment_id,
            {}
        )

        try:
            priority_weight = Decimal(
                str(priority_info.get("priority_weight", 1.0))
            )
        except Exception:
            priority_weight = Decimal("1.0")

        if priority_weight <= 0:
            priority_weight = Decimal("1.0")

        # Weighted benefit is used only by the optimization objective.
        weighted_benefit = to_scaled_integer(
            reduction * priority_weight
        )

        valid_investments.append({
            "investment": investment,
            "cost": to_scaled_integer(cost),
            "reduction": to_scaled_integer(reduction),
            "priority_weight": float(priority_weight),
            "weighted_benefit": weighted_benefit,
            "priority_reasons": priority_info.get(
                "priority_reasons",
                []
            ),
            "matched_asset_ids": priority_info.get(
                "matched_asset_ids",
                []
            ),
            "matched_control_ids": priority_info.get(
                "matched_control_ids",
                []
            ),
        })

    if not valid_investments:
        raise ValueError(
            "No investments have valid positive estimated risk reductions."
        )

    # Create the optimization model.
    model = cp_model.CpModel()

    # Each investment has a binary selection variable.
    selected = [
        model.new_bool_var(
            f"investment_{item['investment'].investment_id}"
        )
        for item in valid_investments
    ]

    # Constraint 1: total investment must fit the budget.
    model.add(
        sum(
            item["cost"] * selected[i]
            for i, item in enumerate(valid_investments)
        ) <= budget_cents
    )

    # Constraint 2: actual estimated risk reduction cannot
    # exceed the organization's baseline risk.
    model.add(
        sum(
            item["reduction"] * selected[i]
            for i, item in enumerate(valid_investments)
        ) <= baseline_risk_units
    )

    # Objective: maximize priority-weighted estimated risk reduction.
    model.maximize(
        sum(
            item["weighted_benefit"] * selected[i]
            for i, item in enumerate(valid_investments)
        )
    )

    # Solve.
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10.0
    solver.parameters.num_search_workers = 8

    status = solver.solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise ValueError(
            "The optimization solver could not find a feasible solution."
        )

    # Collect selected investments.
    selected_investments = []

    total_investment = 0
    total_risk_reduction = 0

    for i, item in enumerate(valid_investments):

        if solver.value(selected[i]) == 1:

            investment = item["investment"]

            selected_investments.append({
                "investment_id": investment.investment_id,
                "investment_name": investment.investment_name,

                "recommended_amount": round(
                    item["cost"] / 100,
                    2
                ),

                "expected_risk_reduction": round(
                    item["reduction"] / 100,
                    2
                ),

                "priority_weight": item["priority_weight"],

                "priority_adjusted_benefit": round(
                    item["weighted_benefit"] / 100,
                    2
                ),

                "priority_reasons": item["priority_reasons"],

                "matched_asset_ids": item["matched_asset_ids"],

                "matched_control_ids": item["matched_control_ids"],
            })

            total_investment += item["cost"]
            total_risk_reduction += item["reduction"]

    risk_before = baseline_risk

    risk_after = max(
        0.0,
        round(
            risk_before - (total_risk_reduction / 100),
            2
        )
    )

    return {
        "selected_investments": selected_investments,

        "total_investment": round(
            total_investment / 100,
            2
        ),

        "available_budget": round(
            budget_cents / 100,
            2
        ),

        "remaining_budget": round(
            (budget_cents - total_investment) / 100,
            2
        ),

        "estimated_risk_before": round(
            risk_before,
            2
        ),

        "estimated_risk_reduction": round(
            total_risk_reduction / 100,
            2
        ),

        "estimated_risk_after": risk_after,

        "solver_status": (
            "Optimal"
            if status == cp_model.OPTIMAL
            else "Feasible"
        ),

        "methodology": (
            "OR-Tools Predictive-Priority-Weighted "
            "Budget-Constrained Investment Optimization v2"
        ),

        "optimization_objective": (
            "Maximize predictive-priority-weighted "
            "estimated risk reduction"
        ),

        "constraints": [
            "Total investment must not exceed available budget.",
            "Total actual estimated risk reduction cannot exceed baseline risk.",
            "Each investment is either fully selected or rejected.",
            "Predictive priority weights affect selection priority, "
            "not the reported estimated risk reduction."
        ],
    }
