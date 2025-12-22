import warnings
from enum import Enum
from typing import Annotated, Any, Literal, cast

import numpy as np
import numpy.linalg as LA  # noqa: N812
import numpy.typing as npt
from typing_extensions import Doc

from pdag._core.parameter import BooleanParameter, CategoricalParameter, LiteralValueType, ParameterABC, RealParameter
from pdag._exec import ParameterId


def inverse_distance_real(
    parameter: RealParameter,
    distance: float,
    *,
    rng: np.random.Generator,
) -> float:
    """Inverse distance function for real parameters."""
    assert parameter.lower_bound is not None, f"Parameter {parameter} has no lower bound."
    assert parameter.upper_bound is not None, f"Parameter {parameter} has no upper bound."

    if "nominal" in parameter.metadata:
        nominal: float = parameter.metadata["nominal"]
    else:
        warnings.warn(f"Parameter {parameter} has no nominal value. Using the midpoint of the range.", stacklevel=2)
        nominal = (parameter.lower_bound + parameter.upper_bound) / 2

    # There are two possible values for one distance. We choose one randomly.
    if rng.uniform() < 0.5:  # noqa: PLR2004
        return nominal + distance * (parameter.upper_bound - nominal)
    return nominal - distance * (nominal - parameter.lower_bound)


def _calc_distance_real(
    parameter: RealParameter,
    value: float,
) -> float:
    assert parameter.lower_bound is not None, f"Parameter {parameter} has no lower bound."
    assert parameter.upper_bound is not None, f"Parameter {parameter} has no upper bound."

    if "nominal" in parameter.metadata:
        nominal: float = parameter.metadata["nominal"]
    else:
        warnings.warn(f"Parameter {parameter} has no nominal value. Using the midpoint of the range.", stacklevel=2)
        nominal = (parameter.lower_bound + parameter.upper_bound) / 2

    if value > nominal:
        return (value - nominal) / (parameter.upper_bound - nominal)
    return (nominal - value) / (nominal - parameter.lower_bound)


def _calc_distance_boolean(
    parameter: BooleanParameter,
    value: bool,  # noqa: FBT001
) -> float:
    if value in parameter.metadata["distance"]:
        disatnce = parameter.metadata["distance"][value]
        assert isinstance(disatnce, float), f"Distance for value {value} is not a float."
        return disatnce
    warnings.warn(f"No distance defined for value {value}. Using 1.", stacklevel=2)
    return 1


def _calc_distance_categorical[T: LiteralValueType](
    parameter: CategoricalParameter[T],
    value: T,
) -> float:
    if value in parameter.metadata["distance"]:
        distance = parameter.metadata["distance"][value]
        assert isinstance(distance, float), f"Distance for value {value!r} is not a float."
        return distance
    warnings.warn(f"No distance defined for value {value!r}. Using 1.", stacklevel=2)
    return 1


def calc_distance[T](
    parameter: Annotated[ParameterABC[T], Doc("A Pdag parameter.")],
    value: T,
) -> float:
    if isinstance(parameter, RealParameter):
        assert isinstance(value, float), f"Value {value} is not a float."
        return _calc_distance_real(parameter, value)
    if isinstance(parameter, BooleanParameter):
        assert isinstance(value, bool), f"Value {value} is not a bool."
        return _calc_distance_boolean(parameter, value)
    if isinstance(parameter, CategoricalParameter):
        assert isinstance(value, int | bytes | str | bool | Enum | None), f"Value {value} is not a literal value."
        return _calc_distance_categorical(parameter, value)

    msg = f"Unsupported parameter type: {type(parameter)}"
    raise ValueError(msg)


def normalize(
    x: npt.NDArray[np.number[Any]],
    ord: None | float | Literal["fro", "nuc"] = None,  # noqa: A002
    axis: None | int = None,
) -> npt.NDArray[np.floating[Any]]:
    norm: npt.NDArray[np.floating[Any]] = LA.norm(x, ord=ord, axis=axis, keepdims=True)
    return np.where(norm == 0.0, x, x.astype(np.float64) / norm)


def distance_constrained_sampling(
    parameters: dict[ParameterId, ParameterABC[Any]],
    n_samples: int,
    *,
    budget: float,
    rng: np.random.Generator | None = None,
    uniform_in_distance: bool = True,
) -> list[dict[ParameterId, Any]]:
    if not all(isinstance(parameter, RealParameter) for parameter in parameters.values()):
        msg = "Only real parameters are supported."
        raise NotImplementedError(msg)

    n_parameters = len(parameters)
    rng = np.random.default_rng() if rng is None else rng
    direction_samples = normalize(rng.normal(size=(n_samples, n_parameters)), axis=-1)
    radius_samples_normalized = (
        rng.uniform(size=n_samples) if uniform_in_distance else np.pow(rng.uniform(size=n_samples), 1 / n_parameters)
    )
    radius_samples = budget * radius_samples_normalized
    distance_samples = np.abs(radius_samples[:, np.newaxis] * direction_samples)

    # TODO: Support other parameter types apart from RealParameter
    return [
        {
            parameter_id: inverse_distance_real(cast("RealParameter", parameter), distance, rng=rng)
            for (parameter_id, parameter), distance in zip(parameters.items(), distance_sample, strict=True)
        }
        for distance_sample in distance_samples
    ]
