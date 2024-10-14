from collections.abc import Hashable
from dataclasses import dataclass, field

from ._model import ParameterBase


@dataclass(frozen=True, slots=True)
class BooleanParameter(ParameterBase[bool]): ...


@dataclass(frozen=True, slots=True)
class NumericParameter(ParameterBase[float]):
    unit: str | None = field(default=None, kw_only=True)
    lower_bound: float | None = field(default=None, kw_only=True)
    upper_bound: float | None = field(default=None, kw_only=True)


@dataclass(frozen=True, slots=True)
class CategoricalParameter[T: Hashable](ParameterBase[T]):
    categories: frozenset[T]
