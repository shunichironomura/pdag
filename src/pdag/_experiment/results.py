import random
import string
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from typing import Any

import polars as pl

import pdag


def generate_random_string(length: int = 6) -> str:
    # Return random string
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))  # noqa: S311


def results_to_df(
    results: Iterable[Mapping[pdag.StaticParameterId | pdag.TimeSeriesParameterId, Any]],
    case_id_factory: Callable[[], str] = generate_random_string,
) -> pl.DataFrame:
    rows: list[dict[str, Any]] = []
    for res in results:
        case_id = case_id_factory()
        # Containers for static and time-series parameters.
        static_data: dict[str, Any] = {}
        timeseries_data_dd: defaultdict[int, dict[str, Any]] = defaultdict(dict)
        for parameter_id, value in res.items():
            # We assume that static parameter_ids have only the `name` attribute,
            # while time series parameter_ids have `name` and `time_step` attributes.
            if isinstance(parameter_id, pdag.StaticParameterId):
                static_data[parameter_id.parameter_path_str] = value
            elif isinstance(parameter_id, pdag.TimeSeriesParameterId):
                ts = parameter_id.time_step
                timeseries_data_dd[ts][parameter_id.parameter_path_str] = value

        timeseries_data = dict(timeseries_data_dd)

        # For each time step, create a row that merges static and time-series parameters.
        for ts, ts_params in sorted(timeseries_data.items()):
            row = {"case_id": case_id, "time_step": ts}
            # Include static parameters (repeated for each time step)
            row.update(static_data)
            # Include time-series parameters for the current time step
            row.update(ts_params)
            rows.append(row)

    return pl.DataFrame(rows)
