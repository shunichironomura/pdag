from collections.abc import Generator, Iterable, Mapping
from typing import Any, Literal, overload

import polars as pl
from tqdm import tqdm

from pdag._exec import ExecutionModel, ParameterId, execute_exec_model

from .results import results_to_df


def _infinite_empty_dict_generator() -> Generator[dict[str, Any]]:
    while True:
        yield {}


@overload
def run_experiments(
    exec_model: ExecutionModel,
    cases: Iterable[Mapping[ParameterId, Any]],
    *,
    metadata: Iterable[Mapping[str, Any]],
    return_type: Literal["list"],
    n_cases: int | None = None,
) -> list[dict[ParameterId, Any]]: ...
@overload
def run_experiments(
    exec_model: ExecutionModel,
    cases: Iterable[Mapping[ParameterId, Any]],
    *,
    metadata: None = None,
    return_type: Literal["list"],
    n_cases: int | None = None,
) -> list[dict[ParameterId | str, Any]]: ...
@overload
def run_experiments(
    exec_model: ExecutionModel,
    cases: Iterable[Mapping[ParameterId, Any]],
    *,
    metadata: Iterable[Mapping[str, Any]] | None = None,
    return_type: Literal["polars"] = "polars",
    n_cases: int | None = None,
) -> pl.DataFrame: ...


def run_experiments(
    exec_model: ExecutionModel,
    cases: Iterable[Mapping[ParameterId, Any]],
    *,
    metadata: Iterable[Mapping[str, Any]] | None = None,
    return_type: Literal["list", "polars"] = "polars",
    n_cases: int | None = None,
) -> list[dict[ParameterId, Any]] | list[dict[ParameterId | str, Any]] | pl.DataFrame:
    results_iter = (
        execute_exec_model(
            exec_model,
            inputs=case,
        )
        | {"metadata": mtd}
        for case, mtd in tqdm(
            zip(cases, metadata if metadata is not None else _infinite_empty_dict_generator(), strict=False),
            total=n_cases,
        )
    )
    match return_type:
        case "list":
            return list(results_iter)
        case "polars":
            return results_to_df(results_iter)
        case _:
            msg = f"Invalid return_type: {return_type}"
            raise ValueError(msg)
