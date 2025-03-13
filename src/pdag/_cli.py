import importlib.metadata
from pathlib import Path
from typing import Annotated, NoReturn, Optional

import typer

from pdag._export.watch import watch_model

app = typer.Typer()


def version_callback(value: bool) -> None:  # noqa: FBT001
    if value:
        version = importlib.metadata.version("pdag")
        typer.echo(f"pdag {version}")
        raise typer.Exit


@app.callback()
def main(
    version: Annotated[
        Optional[bool],  # noqa: UP007
        typer.Option("--version", help="Show the version and exit", is_eager=True, callback=version_callback),
    ] = None,
) -> None:
    """Pdag CLI."""


@app.command()
def watch(
    model: Annotated[str, typer.Argument(..., help="Model specified as 'module_name:ModelName'")],
    output_path: Annotated[Path, typer.Argument(..., help="Path to output file")],
) -> NoReturn:
    """Watch a model."""
    module_str, _, attr_str = model.partition(":")
    if not attr_str:
        msg = "Model must be specified as 'module_name:ModelName'"
        raise typer.BadParameter(msg)
    watch_model(module_str, attr_str, output_path)
