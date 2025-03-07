from collections.abc import Iterable, Mapping
from typing import Any, Literal, overload

import polars as pl
from tqdm import tqdm

from pdag._exec import ExecutionModel, ParameterId, execute_exec_model

from .results import results_to_df


@overload
def run_experiments(
    exec_model: ExecutionModel,
    cases: Iterable[Mapping[ParameterId, Any]],
    *,
    return_type: Literal["list"],
    n_cases: int | None = None,
) -> list[dict[ParameterId, Any]]: ...


@overload
def run_experiments(
    exec_model: ExecutionModel,
    cases: Iterable[Mapping[ParameterId, Any]],
    *,
    return_type: Literal["polars"] = "polars",
    n_cases: int | None = None,
) -> pl.DataFrame: ...
def run_experiments(
    exec_model: ExecutionModel,
    cases: Iterable[Mapping[ParameterId, Any]],
    *,
    return_type: Literal["list", "polars"] = "polars",
    n_cases: int | None = None,
) -> list[dict[ParameterId, Any]] | pl.DataFrame:
    results_iter = (
        execute_exec_model(
            exec_model,
            inputs=case,
        )
        for case in tqdm(cases, total=n_cases)
    )
    match return_type:
        case "list":
            return list(results_iter)
        case "polars":
            return results_to_df(results_iter)
        case _:
            msg = f"Invalid return_type: {return_type}"
            raise ValueError(msg)
