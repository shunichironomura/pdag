import inspect
from collections.abc import Callable


def relationship[R, **P](func: Callable[P, R]) -> Callable[P, R]:
    """Decorate a function to mark it as a relationship."""
    func.__is_pdag_relationship__ = True  # type: ignore[attr-defined]
    source = inspect.getsource(func)
    func.__pdag_source__ = source  # type: ignore[attr-defined]
    return func
