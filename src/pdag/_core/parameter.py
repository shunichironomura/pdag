from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from types import EllipsisType
from typing import Any, ClassVar

from pdag.utils import InitArgsRecorder

from .reference import ParameterRef


@dataclass
class ParameterABC[T](InitArgsRecorder, ABC):
    type: ClassVar[str] = "base"
    _name: str | EllipsisType
    is_time_series: bool = field(default=False, kw_only=True)
    metadata: dict[str, Any] = field(default_factory=dict, kw_only=True)

    def is_hydrated(self) -> bool:
        return isinstance(self._name, str)

    def name_is_set(self) -> bool:
        return isinstance(self._name, str)

    @property
    def name(self) -> str:
        if isinstance(self._name, EllipsisType):
            msg = "Parameter name has not been set."
            raise ValueError(msg)  # noqa: TRY004
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    @abstractmethod
    def get_type_hint(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def from_unit_interval(self, value: float) -> T:
        raise NotImplementedError

    def ref(
        self,
        *,
        previous: bool = False,
        next: bool = False,  # noqa: A002
        initial: bool = False,
        all_time_steps: bool = False,
    ) -> ParameterRef:
        return ParameterRef(
            name=self.name,
            previous=previous,
            next=next,
            initial=initial,
            all_time_steps=all_time_steps,
        )


@dataclass
class RealParameter(ParameterABC[float]):
    type: ClassVar[str] = "real"
    unit: str | None = None
    lower_bound: float | None = None
    upper_bound: float | None = None

    def get_type_hint(self) -> str:
        return "float"

    def from_unit_interval(self, value: float) -> float:
        if self.lower_bound is None or self.upper_bound is None:
            msg = f"Lower and upper bounds must be set to convert from unit interval. Parameter: {self.name}"
            raise ValueError(msg)
        return self.lower_bound + value * (self.upper_bound - self.lower_bound)


@dataclass
class BooleanParameter(ParameterABC[bool]):
    type: ClassVar[str] = "boolean"

    def get_type_hint(self) -> str:
        return "bool"

    def from_unit_interval(self, value: float) -> bool:
        return value >= 0.5  # noqa: PLR2004


type LiteralValueType = int | bytes | str | bool | Enum | None


@dataclass
class CategoricalParameter[T: LiteralValueType](ParameterABC[T]):
    type: ClassVar[str] = "categorical"
    categories: tuple[T, ...]

    def get_type_hint(self) -> str:
        return f"Literal[{', '.join(self._to_type_hint(category) for category in self.categories)}]"

    @staticmethod
    def _to_type_hint(category: LiteralValueType) -> str:
        if isinstance(category, Enum):
            return f"{category.__class__.__name__}.{category.name}"
        return repr(category)

    def from_unit_interval(self, value: float) -> T:
        return self.categories[int(value * len(self.categories))]
