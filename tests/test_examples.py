from typing import Any

import pytest

import pdag
from pdag.examples import DiamondMdpModel, PolynomialModel, SquareModel, TwoSquares

MODELS = [
    DiamondMdpModel,
    PolynomialModel,
    SquareModel,
    TwoSquares,
]

N_TIME_STEPS: dict[type[pdag.Model], int] = {
    DiamondMdpModel: 5,
    PolynomialModel: 1,
    SquareModel: 1,
    TwoSquares: 1,
}

INPUTS = {
    DiamondMdpModel: {
        pdag.StaticParameterId((), "policy"): "left",
        pdag.TimeSeriesParameterId((), "location", 0): "start",
    },
    PolynomialModel: {
        pdag.StaticParameterId((), "a[0]"): 1.0,
        pdag.StaticParameterId((), "a[1]"): 2.0,
        pdag.StaticParameterId((), "a[2]"): 3.0,
        pdag.StaticParameterId((), "x"): 2.0,
    },
    SquareModel: {
        pdag.StaticParameterId((), "x"): 2.0,
    },
    TwoSquares: {
        pdag.StaticParameterId((), "x"): 4.0,
        pdag.StaticParameterId((), "y"): 5.0,
    },
}

RESULTS: dict[type[pdag.Model], dict[pdag.ParameterId, Any]] = {
    DiamondMdpModel: {
        pdag.StaticParameterId(model_path=(), name="policy"): "left",
        pdag.TimeSeriesParameterId(model_path=(), name="location", time_step=0): "start",
        pdag.TimeSeriesParameterId(model_path=(), name="reward", time_step=0): 0.0,
        pdag.TimeSeriesParameterId(model_path=(), name="action", time_step=0): "go_left",
        pdag.TimeSeriesParameterId(model_path=(), name="location", time_step=1): "left",
        pdag.TimeSeriesParameterId(model_path=(), name="reward", time_step=1): 0.0,
        pdag.TimeSeriesParameterId(model_path=(), name="action", time_step=1): "move_forward",
        pdag.TimeSeriesParameterId(model_path=(), name="location", time_step=2): "end",
        pdag.TimeSeriesParameterId(model_path=(), name="reward", time_step=2): 1.0,
        pdag.TimeSeriesParameterId(model_path=(), name="action", time_step=2): "none",
        pdag.TimeSeriesParameterId(model_path=(), name="location", time_step=3): "end",
        pdag.TimeSeriesParameterId(model_path=(), name="action", time_step=3): "none",
        pdag.TimeSeriesParameterId(model_path=(), name="reward", time_step=3): 0.0,
        pdag.TimeSeriesParameterId(model_path=(), name="location", time_step=4): "end",
        pdag.TimeSeriesParameterId(model_path=(), name="action", time_step=4): "none",
        pdag.TimeSeriesParameterId(model_path=(), name="reward", time_step=4): 0.0,
        pdag.StaticParameterId(model_path=(), name="cumulative_reward"): 1.0,
    },
    PolynomialModel: {
        pdag.StaticParameterId(model_path=(), name="a[2]"): 3.0,
        pdag.StaticParameterId(model_path=(), name="a[1]"): 2.0,
        pdag.StaticParameterId(model_path=(), name="x"): 2.0,
        pdag.StaticParameterId(model_path=(), name="a[0]"): 1.0,
        pdag.StaticParameterId(model_path=("calc_square_term",), name="x"): 2.0,
        pdag.StaticParameterId(model_path=("calc_square_term",), name="y"): 4.0,
        pdag.StaticParameterId(model_path=(), name="x_squared"): 4.0,
        pdag.StaticParameterId(model_path=(), name="y"): 17.0,
    },
    SquareModel: {
        pdag.StaticParameterId(model_path=(), name="x"): 2.0,
        pdag.StaticParameterId(model_path=(), name="y"): 4.0,
    },
    TwoSquares: {
        pdag.StaticParameterId(model_path=(), name="x"): 4.0,
        pdag.StaticParameterId(model_path=(), name="y"): 5.0,
        pdag.StaticParameterId(model_path=("calc_square_term[x]",), name="x"): 4.0,
        pdag.StaticParameterId(model_path=("calc_square_term[y]",), name="x"): 5.0,
        pdag.StaticParameterId(model_path=("calc_square_term[x]",), name="y"): 16.0,
        pdag.StaticParameterId(model_path=("calc_square_term[y]",), name="y"): 25.0,
        pdag.StaticParameterId(model_path=(), name="x_squared"): 16.0,
        pdag.StaticParameterId(model_path=(), name="y_squared"): 25.0,
        pdag.StaticParameterId(model_path=(), name="z"): 41.0,
    },
}


@pytest.mark.parametrize("model", MODELS)
def test_model_to_core_model(model: type[pdag.Model]) -> None:
    """Test that the model can be converted to a core model."""
    _core_model = model.to_core_model()


@pytest.mark.parametrize(("model", "n_time_steps"), N_TIME_STEPS.items())
def test_model_to_exec_model(model: type[pdag.Model], n_time_steps: int) -> None:
    """Test that the model can be converted to an exec model."""
    core_model = model.to_core_model()
    _exec_model = pdag.create_exec_model_from_core_model(core_model, n_time_steps=n_time_steps)


@pytest.mark.parametrize(
    ("model", "n_time_steps", "inputs", "results_expected"),
    [(model, N_TIME_STEPS[model], INPUTS[model], RESULTS[model]) for model in MODELS],
)
def test_model_to_exec_model_and_execute(
    model: type[pdag.Model],
    n_time_steps: int,
    inputs: dict[pdag.ParameterId, Any],
    results_expected: dict[pdag.ParameterId, Any],
) -> None:
    """Test that the model can be converted to an exec model and executed."""
    core_model = model.to_core_model()
    exec_model = pdag.create_exec_model_from_core_model(core_model, n_time_steps=n_time_steps)
    results = pdag.execute_exec_model(
        exec_model,
        inputs=inputs,
    )
    assert results == results_expected, f"Expected {results_expected}, but got {results}"
