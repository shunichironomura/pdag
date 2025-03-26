import importlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

from watchfiles import watch

from .dot import export_dot

if TYPE_CHECKING:
    from pdag._notation import Model

logger = logging.getLogger(__name__)


def watch_model(module_str: str, attr_str: str, output_path: Path) -> NoReturn:
    """Watch a model."""
    try:
        module = importlib.import_module(module_str)
    except Exception as e:
        msg = f"Error importing module {module_str}: {e}"
        raise ValueError(msg) from e

    if module.__file__ is None:
        msg = f"Module {module_str} has no __file__ attribute"
        raise ValueError(msg)

    for _ in watch(module.__file__):
        try:
            module = importlib.reload(module)
            model: Model = getattr(module, attr_str)
        except Exception as e:
            msg = f"Error reloading model {module_str}.{attr_str}: {e}"
            logger.exception(msg)
            continue

        try:
            core_model = model.to_core_model()
        except Exception as e:
            msg = f"Error converting model to core model: {e}"
            logger.exception(msg)
            continue

        try:
            export_dot(core_model, output_path)
        except Exception as e:
            msg = f"Error exporting dot file: {e}"
            logger.exception(msg)
            continue

    msg = "watch() should never return"
    raise RuntimeError(msg)


if __name__ == "__main__":
    import sys

    watch_model(sys.argv[1], sys.argv[2], Path(sys.argv[3]))
