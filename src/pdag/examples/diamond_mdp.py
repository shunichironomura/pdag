"""Diamond MDP model example."""

from typing import Annotated, Literal

import pdag


class DiamondMdpModel(pdag.Model):
    """Diamond MDP model."""

    policy = pdag.CategoricalParameter("policy", categories={"left", "right"})
    location = pdag.CategoricalParameter("location", categories={"start", "left", "right", "end"}, is_time_series=True)
    action = pdag.CategoricalParameter(
        "action",
        categories={"go_left", "go_right", "move_forward", "none"},
        is_time_series=True,
    )
    # Initial value of the reward is not calculated in the model
    reward = pdag.RealParameter("reward", is_time_series=True)
    cumulative_reward = pdag.RealParameter("cumulative_reward")

    @pdag.relationship
    @staticmethod
    def action_selection(  # noqa: D102
        *,
        policy: Annotated[Literal["left", "right"], pdag.ParameterRef("policy")],
        location: Annotated[Literal["start", "left", "right", "end"], pdag.ParameterRef("location")],
    ) -> Annotated[Literal["go_left", "go_right", "move_forward", "none"], pdag.ParameterRef("action")]:
        match location, policy:
            case "start", "left":
                return "go_left"
            case "start", "right":
                return "go_right"
            case "left", "left":
                return "move_forward"
            case "right", "right":
                return "move_forward"
            case "end", _:
                return "none"

        msg = "Invalid policy and location combination"
        raise ValueError(msg)

    @pdag.relationship
    @staticmethod
    def state_transition(  # noqa: D102
        *,
        location: Annotated[Literal["start", "left", "right", "end"], pdag.ParameterRef("location")],
        action: Annotated[Literal["go_left", "go_right", "move_forward", "none"], pdag.ParameterRef("action")],
    ) -> Annotated[Literal["start", "left", "right", "end"], pdag.ParameterRef("location", delayed=True)]:
        match location, action:
            case "start", "go_left":
                return "left"
            case "start", "go_right":
                return "right"
            case "left", "move_forward":
                return "end"
            case "right", "move_forward":
                return "end"
            case "end", _:
                return "end"

        msg = "Invalid location and action combination"
        raise ValueError(msg)

    @pdag.relationship
    @staticmethod
    def reward_function(  # noqa: D102
        *,
        previous_location: Annotated[
            Literal["start", "left", "right", "end"],
            pdag.ParameterRef("location", delayed=True),
        ],
        action: Annotated[Literal["go_left", "go_right", "move_forward", "none"], pdag.ParameterRef("action")],  # noqa: ARG004
        location: Annotated[Literal["start", "left", "right", "end"], pdag.ParameterRef("location")],
    ) -> Annotated[float, pdag.ParameterRef("reward")]:
        if previous_location != "end" and location == "end":
            return 1.0
        return 0.0

    @pdag.relationship
    @staticmethod
    def initial_reward() -> Annotated[float, pdag.ParameterRef("reward", initial=True)]:  # noqa: D102
        return 0.0

    @pdag.relationship
    @staticmethod
    def cumulative_reward_calculation(  # noqa: D102
        *,
        reward: Annotated[list[float], pdag.ParameterRef("reward", all_time_steps=True)],
    ) -> Annotated[float, pdag.ParameterRef("cumulative_reward")]:
        return sum(reward)
