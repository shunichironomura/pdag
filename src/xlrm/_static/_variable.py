from enum import StrEnum
from typing import Literal
import numpy as np
import numpy.typing as npt
from abc import ABC, abstractmethod


class _VariableType(StrEnum):
    X = "X"
    L = "L"
    M = "M"


type VariableTypeArg = _VariableType | Literal["X", "L", "M"] | None


class VariableBase[T: np.generic](ABC):
    def __init__(
        self,
        name: str,
        /,
        *,
        type: VariableTypeArg = None,
    ) -> None:
        self._name = name
        self._type = _VariableType(type) if type else None

    def __hash__(self) -> int:
        return hash(self._name)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VariableBase):
            return NotImplemented
        return self._name == other._name

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._name!r})"

    def __str__(self) -> str:
        return self._name

    @property
    def type(self) -> str | None:
        return self._type.value if self._type else None

    @property
    def name(self) -> str:
        return self._name

    @abstractmethod
    def sample(
        self, size: int | tuple[int, ...] | None = None, rng: np.random.Generator | None = None
    ) -> npt.NDArray[T]:
        raise NotImplementedError


class BooleanVariable(VariableBase[np.bool]):
    def __init__(self, name: str, /, *, type: VariableTypeArg = None) -> None:
        super().__init__(name, type=type)

    def __hash__(self) -> int:
        return hash(self._name)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BooleanVariable):
            return NotImplemented
        return self._name == other._name

    def sample(
        self, size: int | tuple[int, ...] | None = None, rng: np.random.Generator | None = None
    ) -> npt.NDArray[np.bool]:
        if rng is None:
            rng = np.random.default_rng()

        return rng.choice([0, 1], size=size).astype(np.bool)


class NumericVariable(VariableBase[np.float64]):
    def __init__(
        self,
        name: str,
        /,
        *,
        type: VariableTypeArg = None,
        lower_bound: float | None = None,
        upper_bound: float | None = None,
        unit: str | None = None,
    ) -> None:
        super().__init__(name, type=type)
        self._lower_bound = lower_bound
        self._upper_bound = upper_bound
        self._unit = unit

    def __hash__(self) -> int:
        return hash(self._name)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NumericVariable):
            return NotImplemented
        return (
            self._name == other._name
            and self._unit == other._unit
            and self._lower_bound == other._lower_bound
            and self._upper_bound == other._upper_bound
        )

    def sample(
        self, size: int | tuple[int, ...] | None = None, rng: np.random.Generator | None = None
    ) -> npt.NDArray[np.float64]:
        if self._lower_bound is None or self._upper_bound is None:
            raise ValueError(f"Cannot sample from an unbounded variable {self}")

        if rng is None:
            rng = np.random.default_rng()

        return rng.uniform(self._lower_bound, self._upper_bound, size=size)
