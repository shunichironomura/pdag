from dataclasses import dataclass, field
from typing import Any, Callable

from ._parameter import ParameterBase


@dataclass(unsafe_hash=True)
class Relationship:
    function: Callable[..., Any] = field(repr=False, hash=False, compare=False)
    inputs: tuple[ParameterBase[Any], ...]
    outputs: tuple[ParameterBase[Any], ...]
