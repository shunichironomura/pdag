import importlib
import importlib.metadata
import logging
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, NoReturn

import typer
from rich.console import Console
from watchfiles import watch as _watch

from pdag._exec.to_exec_model import create_exec_model_from_core_model
from pdag._export.dot import export_dot

if TYPE_CHECKING:
    from pdag._notation import Model

logger = logging.getLogger(__name__)

console = Console()
err_console = Console(stderr=True)

app = typer.Typer()


def version_callback(value: bool) -> None:  # noqa: FBT001
    if value:
        version = importlib.metadata.version("pdag")
        typer.echo(f"pdag {version}")
        raise typer.Exit


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", help="Show the version and exit", is_eager=True, callback=version_callback),
    ] = None,
) -> None:
    """Pdag CLI."""


@app.command()
def watch(
    model: Annotated[str, typer.Argument(..., help="Model specified as 'module_name:ModelName'")],
    output_path: Annotated[Path, typer.Argument(..., help="Path to output file")],
    *,
    show_locals_on_error: Annotated[bool, typer.Option("--show-locals", help="Show locals on error")] = False,
    try_conversion_to_exec_model: Annotated[
        bool,
        typer.Option("--try-conversion", help="Try conversion to exec model"),
    ] = True,
    n_time_steps: Annotated[int, typer.Option("--n-time-steps", help="Number of time steps for exec model")] = 1,
) -> NoReturn:
    """Watch a model."""
    module_str, _, attr_str = model.partition(":")
    if not attr_str:
        msg = "Model must be specified as 'module_name:ModelName'"
        raise typer.BadParameter(msg)

    try:
        module = importlib.import_module(module_str)
    except Exception as e:
        msg = f"Error importing module {module_str}: {e}"
        raise ValueError(msg) from e

    if module.__file__ is None:
        msg = f"Module {module_str} has no __file__ attribute"
        raise ValueError(msg)

    # Chain a 1-element iterable to execute immediately before the first change is detected
    for _ in chain((None,), _watch(module.__file__)):
        console.clear()
        err_console.clear()

        err_console.print(f":eyes: Watching changes in {module.__file__} for {module_str}:{attr_str}...")

        with err_console.status(f"Loading {module_str}:{attr_str}..."):
            try:
                module = importlib.reload(module)
                pdag_model: Model = getattr(module, attr_str)
            except Exception:  # noqa: BLE001
                err_console.print_exception(show_locals=show_locals_on_error)
                continue

            try:
                core_model = pdag_model.to_core_model()
            except Exception:  # noqa: BLE001
                err_console.print_exception(show_locals=show_locals_on_error)
                continue

            try:
                export_dot(core_model, output_path)
            except Exception:  # noqa: BLE001
                err_console.print_exception(show_locals=show_locals_on_error)
                continue

        err_console.print(f":white_check_mark: Exported {core_model.name} to {output_path}")

        if try_conversion_to_exec_model:
            with err_console.status(f"Creating exec model from {core_model.name} with n_time_steps={n_time_steps}..."):
                try:
                    create_exec_model_from_core_model(
                        core_model,
                        n_time_steps=n_time_steps,
                    )
                except Exception:  # noqa: BLE001
                    err_console.print_exception(show_locals=show_locals_on_error)
                    continue
            err_console.print(f":white_check_mark: Created exec model from {core_model.name}")
            continue

    msg = "`pdag watch` should never return"
    raise RuntimeError(msg)
