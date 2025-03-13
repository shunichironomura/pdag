from pathlib import Path
from typing import Annotated, NoReturn

import typer

from pdag._export.watch import watch_model

app = typer.Typer()


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
