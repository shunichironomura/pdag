from typing import Annotated, Any

import numpy as np
import numpy.typing as npt
from typing_extensions import Doc

from pdag._core import ParameterABC
from pdag._exec import ParameterId


def sample_parameter_values(
    input_parameters: dict[ParameterId, ParameterABC[Any]],
    n_samples: int,
    *,
    rng: np.random.Generator | None = None,
) -> list[dict[ParameterId, Any]]:
    unit_samples_cases = latin_hypercube_sampling(n_samples, len(input_parameters), rng=rng)
    return [
        {
            parameter_id: parameter.from_unit_interval(float(x))
            for (parameter_id, parameter), x in zip(input_parameters.items(), unit_samples, strict=True)
        }
        for unit_samples in unit_samples_cases
    ]


def latin_hypercube_sampling(
    n_samples: Annotated[int, Doc("Number of sample points.")],
    n_dimensions: Annotated[int, Doc("Number of dimensions (parameters).")],
    *,
    rng: Annotated[np.random.Generator | None, Doc("NumPy random number generator.")] = None,
) -> Annotated[npt.NDArray[np.float64], Doc("An array of shape (n_samples, n_dimensions) containing the samples.")]:
    """Generate Latin Hypercube Samples.

    Points are sampled from a unit hypercube in a way that ensures that each row and column contains exactly one sample.
    """
    # Initialize the sample matrix
    result = np.empty((n_samples, n_dimensions))
    # Divide the range [0, 1] into equal intervals
    cut = np.linspace(0, 1, n_samples + 1)

    rng = np.random.default_rng() if rng is None else rng

    # Fill the sample matrix
    for i in range(n_dimensions):
        # Randomly sample within each interval
        result[:, i] = rng.uniform(low=cut[:n_samples], high=cut[1 : n_samples + 1])
        # Shuffle to avoid any correlation between dimensions
        rng.shuffle(result[:, i])

    return result
