from dataclasses import dataclass, field
from typing import Any, Callable

from ._parameter import ParameterBase


@dataclass(frozen=True, slots=True)
class Relationship:
    function: Callable[..., Any] = field(repr=False)
    inputs: tuple[ParameterBase[Any], ...]
    outputs: tuple[ParameterBase[Any], ...]
