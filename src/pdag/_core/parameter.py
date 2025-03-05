from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from types import EllipsisType
from typing import ClassVar

from pdag.utils import InitArgsRecorder


@dataclass
class ParameterABC[T](InitArgsRecorder, ABC):
    type: ClassVar[str] = "base"
    name: str | EllipsisType
    is_time_series: bool = field(default=False, kw_only=True)

    def is_hydrated(self) -> bool:
        return isinstance(self.name, str)

    @abstractmethod
    def get_type_hint(self) -> str:
        raise NotImplementedError


@dataclass
class RealParameter(ParameterABC[float]):
    type: ClassVar[str] = "real"
    unit: str | None = None
    lower_bound: float | None = None
    upper_bound: float | None = None

    def get_type_hint(self) -> str:
        return "float"


@dataclass
class BooleanParameter(ParameterABC[bool]):
    type: ClassVar[str] = "boolean"

    def get_type_hint(self) -> str:
        return "bool"


type LiteralValueType = int | bytes | str | bool | Enum | None


@dataclass
class CategoricalParameter[T: LiteralValueType](ParameterABC[T]):
    type: ClassVar[str] = "categorical"
    categories: set[T]

    def get_type_hint(self) -> str:
        return f"Literal[{', '.join(self._to_type_hint(category) for category in self.categories)}]"

    @staticmethod
    def _to_type_hint(category: LiteralValueType) -> str:
        if isinstance(category, Enum):
            return f"{category.__class__.__name__}.{category.name}"
        return repr(category)
