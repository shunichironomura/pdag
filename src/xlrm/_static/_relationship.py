from ._variable import VariableBase
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Relationship:
    relationship: Callable[..., Any]
    inputs: tuple[VariableBase[Any], ...]
    outputs: tuple[VariableBase[Any], ...]
