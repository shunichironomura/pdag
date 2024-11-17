from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar

from ._model import Model

if TYPE_CHECKING:
    from collections.abc import Callable
    from functools import _Wrapped

    from ._base import ParameterBase

P = ParamSpec("P")
R = TypeVar("R")


def relationship(
    inputs: tuple[ParameterBase[Any], ...] | ParameterBase[Any],
    outputs: tuple[ParameterBase[Any], ...] | ParameterBase[Any],
) -> Callable[[Callable[P, R]], _Wrapped[P, R, P, R]]:
    def decorator(function: Callable[P, R]) -> _Wrapped[P, R, P, R]:
        active_model = Model.get_current()
        active_model.add_relationship(
            function=function,
            inputs=inputs,
            outputs=outputs,
        )

        @wraps(function)
        def inner(*args: P.args, **kwargs: P.kwargs) -> R:
            return function(*args, **kwargs)

        return inner

    return decorator
