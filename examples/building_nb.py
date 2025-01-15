# mypy: disable-error-code=no-untyped-def
import marimo

__generated_with = "0.10.13"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""## Model definition""")


@app.cell
def _():
    import numpy as np

    return (np,)


@app.cell
def _():
    from enum import Enum, auto

    import pdag

    class BuildingState(Enum):
        NONE = auto()
        OPT_33 = auto()
        OPT_57 = auto()
        EXP_33 = auto()
        EXP_57 = auto()

    class Action(Enum):
        NONE = auto()
        BUILD_OPT_33 = auto()
        BUILD_OPT_57 = auto()
        TEAR_DOWN_OPT_33_AND_BUILD_OPT_57 = auto()
        BUILD_EXP_33 = auto()
        EXP_TO_57 = auto()

    class PolicyType(Enum):
        NONE = auto()
        BUILD_OPT_57 = auto()
        BUILD_OPT_33_AND_REBUILD = auto()  # needs rebuild threshold
        BUILD_EXP_33_AND_EXPAND = auto()  # needs expand threshold

    with pdag.Model() as building_model:
        # Constants
        n_time_steps = 5
        revenue_per_floor = 3
        action_cost = {
            Action.NONE: 0.0,
            Action.BUILD_OPT_33: 33.0,
            Action.BUILD_OPT_57: 57.0,
            Action.TEAR_DOWN_OPT_33_AND_BUILD_OPT_57: 33 / 2 + 57.0,
            Action.BUILD_EXP_33: 33.0 * 1.2,
            Action.EXP_TO_57: (57.0 - 33.0) / 1.5,
        }
        discount_rate = 0.1

        # Time-series parameters
        building_state_ts: list[pdag.CategoricalParameter[BuildingState]] = [
            pdag.CategoricalParameter(f"bs[{i}]", frozenset(BuildingState)) for i in range(n_time_steps)
        ]
        demand_ts = [pdag.NumericParameter(f"demand[{i}]") for i in range(n_time_steps)]
        action_ts = [pdag.CategoricalParameter(f"action[{i}]", frozenset(Action)) for i in range(n_time_steps)]
        revenue_ts = [pdag.NumericParameter(f"revenue[{i}]") for i in range(n_time_steps)]
        cost_ts = [pdag.NumericParameter(f"cost[{i}]") for i in range(n_time_steps)]
        profit_ts = tuple(pdag.NumericParameter(f"profit[{i}]") for i in range(n_time_steps))

        # Static parameters
        policy_type = pdag.CategoricalParameter("policy_type", frozenset(PolicyType))
        rebuild_threshold = pdag.NumericParameter("rebuild_threshold")
        expand_threshold = pdag.NumericParameter("expand_threshold")
        npv = pdag.NumericParameter("npv")

        # Define action
        # @pdag.relationship((), action_ts[0])
        # def first_action() -> Action:
        #     return Action.NONE

        for t in range(n_time_steps):

            @pdag.relationship(
                (policy_type, demand_ts[t], building_state_ts[t], rebuild_threshold, expand_threshold),
                action_ts[t],
            )
            def determine_action(  # noqa: PLR0911, PLR0912
                policy_type: PolicyType,
                demand: float,
                building_state: BuildingState,
                rebuild_threshold: float,
                expand_threshold: float,
            ) -> Action:
                match policy_type:
                    case PolicyType.NONE:
                        return Action.NONE
                    case PolicyType.BUILD_OPT_57:
                        if building_state == BuildingState.NONE:
                            return Action.BUILD_OPT_57
                        if building_state == BuildingState.OPT_57:
                            return Action.NONE
                    case PolicyType.BUILD_OPT_33_AND_REBUILD:
                        if building_state == BuildingState.NONE:
                            return Action.BUILD_OPT_33
                        if building_state == BuildingState.OPT_33:
                            if demand >= rebuild_threshold:
                                return Action.TEAR_DOWN_OPT_33_AND_BUILD_OPT_57
                            return Action.NONE
                        if building_state == BuildingState.OPT_57:
                            return Action.NONE
                    case PolicyType.BUILD_EXP_33_AND_EXPAND:
                        if building_state == BuildingState.NONE:
                            return Action.BUILD_EXP_33
                        if building_state == BuildingState.EXP_33:
                            if demand >= expand_threshold:
                                return Action.EXP_TO_57
                            return Action.NONE
                        if building_state == BuildingState.EXP_57:
                            return Action.NONE
                msg = f"Should not reach here: {policy_type=}"
                raise ValueError(msg)

        # Define state evolution
        @pdag.relationship((), building_state_ts[0])
        def first_state() -> BuildingState:
            return BuildingState.NONE

        for t in range(n_time_steps - 1):

            @pdag.relationship((building_state_ts[t], action_ts[t]), building_state_ts[t + 1])
            def evolve_state(building_state: BuildingState, action: Action) -> BuildingState:
                match building_state:
                    case BuildingState.NONE:
                        if action == Action.BUILD_OPT_33:
                            return BuildingState.OPT_33
                        if action == Action.BUILD_OPT_57:
                            return BuildingState.OPT_57
                        if action == Action.BUILD_EXP_33:
                            return BuildingState.EXP_33
                    case BuildingState.OPT_33:
                        if action == Action.TEAR_DOWN_OPT_33_AND_BUILD_OPT_57:
                            return BuildingState.OPT_57
                    case BuildingState.OPT_57:
                        pass
                    case BuildingState.EXP_33:
                        if action == Action.EXP_TO_57:
                            return BuildingState.EXP_57
                    case BuildingState.EXP_57:
                        pass
                return building_state

        for t in range(n_time_steps):
            # Calculate revenue
            @pdag.relationship((building_state_ts[t], demand_ts[t]), revenue_ts[t])
            def calculate_revenue(building_state: BuildingState, demand: float) -> float:
                return revenue_per_floor * min(
                    {
                        BuildingState.NONE: 0,
                        BuildingState.OPT_33: 33,
                        BuildingState.OPT_57: 57,
                        BuildingState.EXP_33: 33,
                        BuildingState.EXP_57: 57,
                    }[building_state],
                    demand,
                )

            # Calculate cost
            @pdag.relationship(action_ts[t], cost_ts[t])
            def calculate_cost(action: Action) -> float:
                return action_cost[action]

            # Calcualte profit
            @pdag.relationship((revenue_ts[t], cost_ts[t]), profit_ts[t])
            def calculate_profit(revenue: float, cost: float) -> float:
                return revenue - cost

        # Calculate NPV
        @pdag.relationship(profit_ts, npv)
        def calculate_npv(*profits: float) -> float:
            return sum(profit / (1 + discount_rate) ** i for i, profit in enumerate(profits))

    return (
        Action,
        BuildingState,
        Enum,
        PolicyType,
        action_cost,
        action_ts,
        auto,
        building_model,
        building_state_ts,
        calculate_cost,
        calculate_npv,
        calculate_profit,
        calculate_revenue,
        cost_ts,
        demand_ts,
        determine_action,
        discount_rate,
        evolve_state,
        expand_threshold,
        first_state,
        n_time_steps,
        npv,
        pdag,
        policy_type,
        profit_ts,
        rebuild_threshold,
        revenue_per_floor,
        revenue_ts,
        t,
    )


@app.cell
def _(building_model, mo):
    building_model.to_pydot().write_png("building_model.png")
    mo.image(src="building_model.png")


@app.cell
def _(
    PolicyType,
    demand_scenarios,
    demand_ts,
    expand_threshold,
    policy_type,
    rebuild_threshold,
):
    from itertools import product

    # Policy parameters: policy_type, rebuild_threshold, expand_threshold
    # Exogenous parameters: demand_ts
    policy_type_values = list(PolicyType)
    rebuild_threshold_values = [0, 20, 40, 60]
    expand_threshold_values = [0, 20, 40, 60]
    policies = [
        {
            policy_type: policy_type_value,
            rebuild_threshold: rebuild_threshold_value,
            expand_threshold: expand_threshold_value,
        }
        for policy_type_value, rebuild_threshold_value, expand_threshold_value in product(
            policy_type_values,
            rebuild_threshold_values,
            expand_threshold_values,
        )
    ]

    # demand_scenarios = [[0, 0, 0], [0, 0, 20], [0, 20, 20], [20, 20, 20]]
    scenarios = [
        {demand_ts[t]: demand for t, demand in enumerate(demand_scenario)} for demand_scenario in demand_scenarios
    ]

    experiments = [scenario | policy for scenario, policy in product(scenarios, policies)]
    len(experiments)
    return (
        expand_threshold_values,
        experiments,
        policies,
        policy_type_values,
        product,
        rebuild_threshold_values,
        scenarios,
    )


@app.cell
def _(n_time_steps, np):
    rng = np.random.default_rng()
    n_demand_scenarios = 5
    demand_delta_values = rng.uniform(0.0, 50.0, (n_demand_scenarios, n_time_steps - 1))

    demand_scenarios = np.zeros((n_demand_scenarios, n_time_steps))
    demand_scenarios[:, 1:] = np.cumsum(demand_delta_values, axis=-1)
    return demand_delta_values, demand_scenarios, n_demand_scenarios, rng


@app.cell
def _(building_model, experiments, mo):
    import pandas as pd

    results = [
        {parameter.name: value for parameter, value in building_model.evaluate(experiment).items()}
        for experiment in mo.status.progress_bar(experiments)
    ]
    results_df = pd.DataFrame(results)
    results_df
    return pd, results, results_df


@app.cell
def _(n_time_steps, np, results_df):
    ts_cols = ("demand", "action", "bs", "revenue", "cost", "profit")
    static_cols = ("policy_type", "rebuild_threshold", "expand_threshold")
    snapshot_dfs = [
        results_df[list(static_cols) + [f"{_col}[{_t}]" for _col in ts_cols]].rename(
            columns={f"{_col}[{_t}]": _col for _col in ts_cols},
        )
        for _t in range(n_time_steps)
    ]
    for _t in range(n_time_steps):
        #     print({f"{_col}[{_t}]": _col for _col in ts_cols})
        snapshot_dfs[_t]["time"] = _t
        snapshot_dfs[_t]["policy_index"] = np.arange(len(snapshot_dfs[_t]))
    return snapshot_dfs, static_cols, ts_cols


@app.cell
def _(snapshot_dfs):
    snapshot_dfs[0]


@app.cell
def _(pd, snapshot_dfs):
    snapshot_df = pd.concat(snapshot_dfs)
    snapshot_df
    return (snapshot_df,)


@app.cell
def _(snapshot_df):
    snapshot_df[snapshot_df["policy_index"] == 95]  # noqa: PLR2004


@app.cell
def _(mo, snapshot_df):
    import altair as alt

    chart = (
        alt.Chart(snapshot_df)
        .mark_line(point=True)
        .encode(
            x="time",
            y="profit",
            # y="demand",
            color="policy_type",
            detail="policy_index",
        )
    )

    chart = mo.ui.altair_chart(chart)
    return alt, chart


@app.cell
def _(chart, mo):
    mo.hstack([chart, chart.value])


@app.cell
def _(alt, mo, results_df):
    _df = results_df
    chart_exp = (
        alt.Chart(_df)
        .mark_point()
        .encode(
            x="expand_threshold",
            y="npv",
            color="policy_type",
        )
    )
    chart_exp = mo.ui.altair_chart(chart_exp)
    return (chart_exp,)


@app.cell
def _(chart_exp, mo):
    mo.hstack([chart_exp, chart_exp.value])


@app.cell
def _():
    import marimo as mo

    return (mo,)


if __name__ == "__main__":
    app.run()
