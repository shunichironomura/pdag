import importlib
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

from watchfiles import watch

from .dot import export_dot

if TYPE_CHECKING:
    from pdag._notation import Model


def watch_model(module_str: str, attr_str: str, output_path: Path) -> NoReturn:
    """Watch a model."""
    module = importlib.import_module(module_str)
    if module.__file__ is None:
        msg = f"Module {module_str} has no __file__ attribute"
        raise ValueError(msg)

    for _ in watch(module.__file__):
        module = importlib.reload(module)
        model: Model = getattr(module, attr_str)
        core_model = model.to_core_model()

        export_dot(core_model, output_path)

    msg = "watch() should never return"
    raise RuntimeError(msg)


if __name__ == "__main__":
    import sys

    watch_model(sys.argv[1], sys.argv[2], Path(sys.argv[3]))
