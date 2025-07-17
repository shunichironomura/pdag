from typing import Annotated

from pydantic import BaseModel

import pdag

COLS = 3
ROWS = 3


class Cell(BaseModel):
    """A cell in a grid."""

    col: Annotated[int, pdag.RealParameter("col", lower_bound=0, upper_bound=COLS - 1)]
    row: Annotated[int, pdag.RealParameter("row", lower_bound=0, upper_bound=ROWS - 1)]


INITIAL_LOCATION = Cell(col=0, row=0)
EXIT = Cell(col=COLS - 1, row=ROWS - 1)


class AgentPolicy(BaseModel):
    """Agent policy for the treasure model."""

    type: Annotated[str, pdag.CategoricalParameter("type", categories=("sweep", "shortest"))]


class TreasureModel(pdag.Model):
    # Unknown parameters
    treasure_location = pdag.PydanticParameter("treasure_location", Cell)

    # Known parameters
    time_limit = pdag.RealParameter("time_limit")

    agent_location = pdag.PydanticParameter("agent_location", Cell, is_time_series=True)

    agent_policy = pdag.PydanticParameter("agent_policy", AgentPolicy)
    agent_action = pdag.CategoricalParameter(
        "agent_action",
        categories=("move_up", "move_down", "move_left", "move_right", "exit"),
        is_time_series=True,
    )

    treasure_found = pdag.BooleanParameter("treasure_found", is_time_series=True)
    exited = pdag.BooleanParameter("exited", is_time_series=True)
    time_limit_reached = pdag.BooleanParameter("time_limit_reached", is_time_series=True)

    @pdag.relationship(at_each_time_step=True)
    @staticmethod
    def determine_action(  # noqa: C901, PLR0911
        agent_location: Annotated[Cell, agent_location.ref()],
        agent_policy: Annotated[AgentPolicy, agent_policy.ref()],
    ) -> Annotated[str, agent_action.ref()]:
        """Determine the agent's action based on the policy."""
        match agent_policy.type:
            case "sweep":
                # Simple sweeping strategy
                match agent_location.row % 2:
                    case 0:  # Even row
                        if agent_location.col < COLS - 1:
                            return "move_right"
                        if agent_location.row < ROWS - 1:
                            return "move_down"
                        return "exit"
                    case 1:  # Odd row
                        if agent_location.col > 0:
                            return "move_left"
                        if agent_location.row < ROWS - 1:
                            return "move_down"
                        msg = f"Invalid location for sweeping strategy: {agent_location}"
                        raise ValueError(msg)
                    case _:
                        msg = f"Invalid location for sweeping strategy: {agent_location}"
                        raise ValueError(msg)
            case "shortest":
                # Shortest path strategy (placeholder logic)
                if agent_location.col < EXIT.col:
                    return "move_right"
                if agent_location.row < EXIT.row:
                    return "move_down"
                return "exit"
            case _:
                msg = f"Unknown agent policy type: {agent_policy.type}"
                raise ValueError(msg)

    @pdag.relationship()
    @staticmethod
    def initial_agent_location() -> Annotated[Cell, agent_location.ref(initial=True)]:
        """Initial agent location."""  # noqa: D401
        return INITIAL_LOCATION

    @pdag.relationship(at_each_time_step=True)
    @staticmethod
    def update_agent_location(  # noqa: C901
        agent_location: Annotated[Cell, agent_location.ref()],
        agent_action: Annotated[str, agent_action.ref()],
        exited: Annotated[bool, exited.ref()],
        time_limit_reached: Annotated[bool, time_limit_reached.ref()],
    ) -> Annotated[Cell, agent_location.ref(next=True)]:
        """Update the agent's location based on the action."""
        if exited or time_limit_reached:
            return agent_location
        new_location = Cell(col=agent_location.col, row=agent_location.row)
        match agent_action:
            case "move_up":
                if new_location.row > 0:
                    new_location.row -= 1
            case "move_down":
                if new_location.row < ROWS - 1:
                    new_location.row += 1
            case "move_left":
                if new_location.col > 0:
                    new_location.col -= 1
            case "move_right":
                if new_location.col < COLS - 1:
                    new_location.col += 1
            case "exit":
                pass
            case _:
                msg = f"Unknown agent action: {agent_action}"
                raise ValueError(msg)
        return new_location

    @pdag.relationship()
    @staticmethod
    def initial_exited() -> Annotated[bool, exited.ref(initial=True)]:
        """Initial exited state."""  # noqa: D401
        return False

    @pdag.relationship(at_each_time_step=True)
    @staticmethod
    def update_exited(
        agent_location: Annotated[Cell, agent_location.ref()],
        agent_action: Annotated[str, agent_action.ref()],
        time_limit_reached: Annotated[bool, time_limit_reached.ref()],
    ) -> Annotated[bool, exited.ref(next=True)]:
        """Check if the agent has exited."""
        return agent_location == EXIT and not time_limit_reached and agent_action == "exit"

    @pdag.relationship()
    @staticmethod
    def initial_treasure_found() -> Annotated[bool, treasure_found.ref(initial=True)]:
        """Initial treasure found state."""  # noqa: D401
        return False

    @pdag.relationship(at_each_time_step=True)
    @staticmethod
    def check_treasure_found(
        agent_location: Annotated[Cell, agent_location.ref()],
        treasure_location: Annotated[Cell, treasure_location.ref()],
        time_limit_reached: Annotated[bool, time_limit_reached.ref()],
        treasure_found: Annotated[bool, treasure_found.ref(previous=True)],
    ) -> Annotated[bool, treasure_found.ref()]:
        """Check if the agent has found the treasure."""
        return treasure_found or (agent_location == treasure_location and not time_limit_reached)

    @pdag.relationship(at_each_time_step=True)
    @staticmethod
    def check_time_limit_reached(
        time_limit: Annotated[float, time_limit.ref()],
        time: Annotated[int, pdag.ExecInfo("time")],
    ) -> Annotated[bool, time_limit_reached.ref()]:
        """Check if the time limit has been reached."""
        return time >= time_limit


if __name__ == "__main__":
    from rich import print  # noqa: A004

    core_model = TreasureModel.to_core_model()
    print(core_model)
    exec_model = pdag.create_exec_model_from_core_model(core_model, n_time_steps=10)
    print(exec_model)
    print(list(exec_model.input_parameter_ids()))
    results = pdag.execute_exec_model(
        exec_model,
        inputs={
            pdag.StaticParameterId((), "treasure_location"): Cell(col=1, row=1),
            pdag.StaticParameterId((), "time_limit"): 10.0,
            pdag.StaticParameterId((), "agent_policy"): AgentPolicy(type="sweep"),
        },
    )
    print(results)
