"""Diamond MDP model example."""

import pdag
from pdag.examples.diamond_mdp import DiamondMdpModel


def test_model_name() -> None:
    assert DiamondMdpModel.name == "DiamondMdpModel"


def test_diamond_mdp() -> None:
    core_model = DiamondMdpModel.to_core_model()
    exec_model = pdag.create_exec_model_from_core_model(core_model, n_time_steps=4)
    results = pdag.execute_exec_model(
        exec_model,
        inputs={
            pdag.StaticParameterId((), "policy"): "left",
            pdag.TimeSeriesParameterId((), "location", 0): "start",
        },
    )
    assert results == {
        pdag.StaticParameterId((), "policy"): "left",
        pdag.TimeSeriesParameterId((), "location", time_step=0): "start",
        pdag.TimeSeriesParameterId((), "reward", time_step=0): 0.0,
        pdag.TimeSeriesParameterId((), "action", time_step=0): "go_left",
        pdag.TimeSeriesParameterId((), "location", time_step=1): "left",
        pdag.TimeSeriesParameterId((), "reward", time_step=1): 0.0,
        pdag.TimeSeriesParameterId((), "action", time_step=1): "move_forward",
        pdag.TimeSeriesParameterId((), "location", time_step=2): "end",
        pdag.TimeSeriesParameterId((), "action", time_step=2): "none",
        pdag.TimeSeriesParameterId((), "reward", time_step=2): 1.0,
        pdag.TimeSeriesParameterId((), "location", time_step=3): "end",
        pdag.TimeSeriesParameterId((), "action", time_step=3): "none",
        pdag.TimeSeriesParameterId((), "reward", time_step=3): 0.0,
        pdag.StaticParameterId((), "cumulative_reward"): 1.0,
    }
