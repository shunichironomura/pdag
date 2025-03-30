import importlib
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

from rich.console import Console
from watchfiles import watch

from pdag._exec.to_exec_model import create_exec_model_from_core_model

from .dot import export_dot

if TYPE_CHECKING:
    from pdag._notation import Model


console = Console()
err_console = Console(stderr=True)


def watch_model(  # noqa: PLR0913
    module_str: str,
    attr_str: str,
    output_path: Path,
    *,
    show_locals_on_error: bool = False,
    try_conversion_to_exec_model: bool = True,
    n_time_steps: int = 1,
) -> NoReturn:
    """Watch a model."""
    try:
        module = importlib.import_module(module_str)
    except Exception as e:
        msg = f"Error importing module {module_str}: {e}"
        raise ValueError(msg) from e

    if module.__file__ is None:
        msg = f"Module {module_str} has no __file__ attribute"
        raise ValueError(msg)

    # Chain a 1-element iterable to execute immediately before the first change is detected
    for _ in chain((None,), watch(module.__file__)):
        console.clear()
        err_console.clear()
        with err_console.status(f"Loading {module_str}:{attr_str}..."):
            try:
                module = importlib.reload(module)
                model: Model = getattr(module, attr_str)
            except Exception:  # noqa: BLE001
                err_console.print_exception(show_locals=show_locals_on_error)
                continue

            try:
                core_model = model.to_core_model()
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

    msg = "watch() should never return"
    raise RuntimeError(msg)


if __name__ == "__main__":
    import sys

    watch_model(sys.argv[1], sys.argv[2], Path(sys.argv[3]))
