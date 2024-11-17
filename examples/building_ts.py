"""The expandable building problem.

It is in one of these states:
- No building
- Optimized 33-story building
- Optimized 57-story building
- Expandable 33-story building
- Expanded 57-story building

Actions:
- Build the optimized 33-story building
- Build the optimized 57-story building
- Tear-down the optimized 33-story building
- Build the expandable 33-story building
- Expand the building to 57 stories

External factors:
- Demand

Time steps:
0. Initial planning & building
1. Demand reveal
2. Second interation of planning & building
"""

from enum import Enum, auto

import pdag
import pdag.ts


# Common types
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


class Policy(Enum):
    NONE = auto()
    BUILD_OPT_57 = auto()
    BUILD_OPT_33_AND_REBUILD = auto()  # needs rebuild threshold
    BUILD_EXP_33_AND_EXPAND = auto()  # needs expand threshold


with pdag.ts.TimeSeriesModel() as building_model:
    # Time-series parameters
    building_state_ts = pdag.ts.CategoricalParameterTs("building_state", frozenset(BuildingState))
    demand_ts = pdag.ts.NumericParameterTs("demand")
    action_ts = pdag.ts.CategoricalParameterTs("action", frozenset(Action))
    revenue_ts = pdag.ts.NumericParameterTs("revenue")
    cost_ts = pdag.ts.NumericParameterTs("cost")

    # Static parameters
    policy = pdag.CategoricalParameter("policy", frozenset(Policy))
    rebuild_threshold = pdag.NumericParameter("rebuild_threshold")
    expand_threshold = pdag.NumericParameter("expand_threshold")
    npv = pdag.NumericParameter("npv")

    # Define action
    @pdag.relationship(policy, pdag.ts.initial(action_ts))
    def set_first_action(policy: Policy) -> Action:  # noqa: ARG001
        return Action.NONE

    @pdag.relationship(
        (policy, demand_ts, building_state_ts, rebuild_threshold, expand_threshold),
        pdag.ts.delayed(action_ts),
    )
    def determine_action(  # noqa: C901, PLR0911, PLR0912, PLR0913
        t: int,  # automatically inserted by pdag  # noqa: ARG001
        policy: Policy,
        demand: float,
        building_state: BuildingState,
        rebuild_threshold: float,
        expand_threshold: float,
    ) -> Action:
        match policy:
            case Policy.NONE:
                return Action.NONE
            case Policy.BUILD_OPT_57:
                if building_state == BuildingState.NONE:
                    return Action.BUILD_OPT_57
                if building_state == BuildingState.OPT_57:
                    return Action.NONE
            case Policy.BUILD_OPT_33_AND_REBUILD:
                if building_state == BuildingState.NONE:
                    return Action.BUILD_OPT_33
                if building_state == BuildingState.OPT_33:
                    if demand >= rebuild_threshold:
                        return Action.TEAR_DOWN_OPT_33_AND_BUILD_OPT_57
                    return Action.NONE
                if building_state == BuildingState.OPT_57:
                    return Action.NONE
            case Policy.BUILD_EXP_33_AND_EXPAND:
                if building_state == BuildingState.NONE:
                    return Action.BUILD_EXP_33
                if building_state == BuildingState.EXP_33:
                    if demand >= expand_threshold:
                        return Action.EXP_TO_57
                    return Action.NONE
        msg = "Should not reach here"
        raise ValueError(msg)

    # Define state evolution
    @pdag.relationship((), pdag.ts.initial(building_state_ts))
    def set_first_state() -> BuildingState:
        return BuildingState.NONE

    @pdag.relationship((building_state_ts, action_ts), pdag.ts.delayed(building_state_ts))
    def evolve_state(t: int, building_state: BuildingState, action: Action) -> BuildingState:  # noqa: ARG001, C901
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

    # Calculate revenue

    @pdag.relationship((building_state_ts, demand_ts), revenue_ts)
    def calculate_revenue(building_state: BuildingState, demand: float) -> float:
        revenue_per_floor = 1
        return revenue_per_floor * max(
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
    @pdag.relationship(action_ts, cost_ts)
    def calculate_cost(action: Action) -> float:
        action_cost = {
            Action.NONE: 0.0,
            Action.BUILD_OPT_33: 33.0,
            Action.BUILD_OPT_57: 57.0,
            Action.TEAR_DOWN_OPT_33_AND_BUILD_OPT_57: 33 / 2 + 57.0,
            Action.BUILD_EXP_33: 33.0 * 1.2,
            Action.EXP_TO_57: (57.0 - 33.0) / 1.5,
        }
        return action_cost[action]

    # Calculate NPV
    @pdag.relationship((revenue_ts, cost_ts), npv)
    def calculate_npv(revenue_ts: tuple[float], cost_ts: tuple[float]) -> float:
        discount_rate = 0.1

        return sum(
            (revenue - cost) / (1 + discount_rate) ** i
            for i, (revenue, cost) in enumerate(zip(revenue_ts, cost_ts, strict=True))
        )
