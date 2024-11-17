from collections.abc import Hashable
from dataclasses import dataclass

from pdag._base import ParameterBase


@dataclass(frozen=True, slots=True)
class ParameterTsBase[T](ParameterBase[T]):
    pass


@dataclass(frozen=True, slots=True)
class BooleanParameterTs(ParameterTsBase[bool]):
    pass


@dataclass(frozen=True, slots=True)
class NumericParameterTs(ParameterTsBase[float]):
    unit: str | None = None
    lower_bound: float | None = None
    upper_bound: float | None = None


@dataclass(frozen=True, slots=True)
class CategoricalParameterTs[T: Hashable](ParameterTsBase[T]):
    categories: frozenset[T]
