from typing import Annotated, Literal

import pdag


class DiamondMdpModel(pdag.Model):
    """Diamond MDP model."""

    policy = pdag.CategoricalParameter("policy", categories=("left", "right"))
    location = pdag.CategoricalParameter("location", categories=("start", "left", "right", "end"), is_time_series=True)
    action = pdag.CategoricalParameter(
        "action",
        categories=("go_left", "go_right", "move_forward", "none"),
        is_time_series=True,
    )
    reward = pdag.RealParameter("reward", is_time_series=True)
    cumulative_reward = pdag.RealParameter("cumulative_reward")

    @pdag.relationship(at_each_time_step=True)
    @staticmethod
    def action_selection(  # noqa: PLR0911
        *,
        policy: Annotated[Literal["left", "right"], policy.ref()],
        location: Annotated[Literal["start", "left", "right", "end"], location.ref()],
    ) -> Annotated[Literal["go_left", "go_right", "move_forward", "none"], action.ref()]:
        match location, policy:
            case "start", "left":
                return "go_left"
            case "start", "right":
                return "go_right"
            case "left", "left":
                return "move_forward"
            case "left", "right":
                return "go_right"
            case "right", "right":
                return "move_forward"
            case "right", "left":
                return "go_left"
            case "end", _:
                return "none"

        msg = f"Invalid policy and location combination: {policy=}, {location=}"
        raise ValueError(msg)

    @pdag.relationship(at_each_time_step=True)
    @staticmethod
    def state_transition(  # noqa: C901, PLR0911
        *,
        location: Annotated[Literal["start", "left", "right", "end"], location.ref()],
        action: Annotated[Literal["go_left", "go_right", "move_forward", "none"], action.ref()],
    ) -> Annotated[Literal["start", "left", "right", "end"], location.ref(next=True)]:
        match location, action:
            case "start", "go_left":
                return "left"
            case "start", "go_right":
                return "right"
            case "start", "move_forward":
                return "start"
            case "left", "move_forward":
                return "end"
            case "left", "go_left":
                return "left"
            case "left", "go_right":
                return "right"
            case "right", "move_forward":
                return "end"
            case "right", "go_left":
                return "left"
            case "right", "go_right":
                return "right"
            case _, "none":
                return location
            case "end", _:
                return "end"

        msg = f"Invalid location and action combination: {location=}, {action=}"
        raise ValueError(msg)

    @pdag.relationship
    @staticmethod
    def initial_reward() -> Annotated[float, reward.ref(initial=True)]:
        return 0.0

    @pdag.relationship(at_each_time_step=True)
    @staticmethod
    def reward_function(
        *,
        previous_location: Annotated[
            Literal["start", "left", "right", "end"],
            location.ref(previous=True),
        ],
        action: Annotated[  # noqa: ARG004
            Literal["go_left", "go_right", "move_forward", "none"],
            action.ref(previous=True),
        ],
        location: Annotated[Literal["start", "left", "right", "end"], location.ref()],
    ) -> Annotated[float, reward.ref()]:
        if previous_location != "end" and location == "end":
            return 1.0
        return 0.0

    @pdag.relationship
    @staticmethod
    def cumulative_reward_calculation(
        *,
        reward: Annotated[list[float], reward.ref(all_time_steps=True)],
    ) -> Annotated[float, cumulative_reward.ref()]:
        return sum(reward)


if __name__ == "__main__":
    from rich import print  # noqa: A004

    core_model = DiamondMdpModel.to_core_model()
    print(core_model)
    exec_model = pdag.create_exec_model_from_core_model(core_model, n_time_steps=4)
    print(exec_model)
    results = pdag.execute_exec_model(
        exec_model,
        inputs={
            pdag.StaticParameterId((), "policy"): "left",
            pdag.TimeSeriesParameterId((), "location", 0): "start",
        },
    )

    print(results)
