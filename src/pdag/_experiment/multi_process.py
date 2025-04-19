from collections import defaultdict
from collections.abc import Iterable, Mapping
from itertools import tee
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import polars as pl
import pyarrow as pa
from mpire import WorkerPool  # type: ignore[attr-defined]
from pyarrow import ipc
from rich.console import Console

import pdag
from pdag._exec.model import ExecutionModel, ParameterId

from .runner import _infinite_empty_dict_generator

console = Console()
err_console = Console(stderr=True)


def _result_to_df_rows(
    result: Mapping[pdag.StaticParameterId | pdag.TimeSeriesParameterId, Any],
    metadata: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    # Containers for static and time-series parameters.
    static_data: dict[str, Any] = {}
    timeseries_data_dd: defaultdict[int, dict[str, Any]] = defaultdict(dict)
    for parameter_id, value in result.items():
        # We assume that static parameter_ids have only the `name` attribute,
        # while time series parameter_ids have `name` and `time_step` attributes.
        if isinstance(parameter_id, pdag.StaticParameterId):
            static_data[parameter_id.parameter_path_str] = value
        elif isinstance(parameter_id, pdag.TimeSeriesParameterId):
            ts = parameter_id.time_step
            timeseries_data_dd[ts][parameter_id.parameter_path_str] = value
    timeseries_data = dict(timeseries_data_dd)

    # For each time step, create a row that merges static and time-series parameters.
    metadata = dict(metadata) if metadata is not None else {}
    if timeseries_data:
        return [{"time_step": ts} | metadata | static_data | ts_params for ts, ts_params in timeseries_data.items()]
    # If there are no time-series parameters, just return the static data.
    return [metadata | static_data]


def _task(
    exec_model: pdag.ExecutionModel,
    case: Mapping[pdag.ParameterId, Any],
    metadata: Mapping[str, Any],
) -> list[dict[str, Any]]:
    result = pdag.execute_exec_model(exec_model, inputs=case)
    return _result_to_df_rows(result, metadata)


def _write_batch(batch: list[dict[str, Any]], writer: ipc.RecordBatchFileWriter, schema: pa.Schema) -> None:
    table = pa.Table.from_pylist(batch, schema=schema)
    writer.write_table(table)


def run_experiments(  # noqa: PLR0913
    exec_model: ExecutionModel,
    cases: Iterable[Mapping[ParameterId, Any]],
    *,
    metadata: Iterable[Mapping[str, Any]] | None = None,
    n_cases: int | None = None,
    delete_arrow_file: bool = True,
    parquet_file_path: str | Path,
) -> None:
    cases_warmup, cases = tee(cases)
    metadata_warmup, metadata = tee(metadata if metadata is not None else _infinite_empty_dict_generator())

    # Create a sample result to get the schema
    sample_result = _task(exec_model, case=next(iter(cases_warmup)), metadata=next(iter(metadata_warmup)))
    schema = pa.Table.from_pylist(sample_result).schema

    # Write the results to an Arrow file
    buffer = []
    batch_size = 1_000
    with TemporaryDirectory(delete=delete_arrow_file) as temp_dir:
        arrow_file_path = Path(temp_dir) / "results.arrow"

        with ipc.RecordBatchFileWriter(str(arrow_file_path), schema=schema) as writer:
            with WorkerPool(shared_objects=exec_model) as pool:
                console.log(f"Running experiments and writing to {arrow_file_path}...")
                for result in pool.imap_unordered(
                    _task,
                    ({"case": case, "metadata": meta} for case, meta in zip(cases, metadata, strict=False)),
                    iterable_len=n_cases,
                    progress_bar=True,
                ):
                    buffer.extend(result)
                    if len(buffer) >= batch_size:
                        _write_batch(buffer, writer, schema)
                        buffer.clear()

            if buffer:
                _write_batch(buffer, writer, schema)

            console.log(f"Finished running experiments. Arrow file written to {arrow_file_path}.")

        # Convert the generated Arrow file to Parquet
        # Experiences have shown that this is faster than writing directly to Parquet.
        with err_console.status("Converting Arrow to Parquet..."):
            lf = pl.scan_ipc(arrow_file_path)
            lf.sink_parquet(parquet_file_path)
        console.log(f"Converted arrow file to parquet file: {parquet_file_path}")

    if delete_arrow_file:
        console.log(f"Arrow file deleted: {arrow_file_path}")
