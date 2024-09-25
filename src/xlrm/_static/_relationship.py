from ._variable import VariableBase
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Relationship:
    function: Callable[..., Any] = field(repr=False)
    inputs: tuple[VariableBase[Any], ...]
    outputs: tuple[VariableBase[Any], ...]
