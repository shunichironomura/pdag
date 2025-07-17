from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from types import EllipsisType
from typing import TYPE_CHECKING, Annotated, Any, ClassVar

from pydantic import BaseModel
from typing_extensions import Doc

from pdag._utils import InitArgsRecorder

from .reference import ParameterRef

if TYPE_CHECKING:
    import builtins


@dataclass
class ParameterABC[T](InitArgsRecorder, ABC):
    """Abstract base class for all parameters."""

    type: ClassVar[
        Annotated[
            str,
            Doc(
                "A string to represent the parameter type. "
                "It is not used now, but may be used in the future for model export.",
            ),
        ]
    ] = "base"
    _name: Annotated[str | EllipsisType, Doc("Name of the parameter.")]
    is_time_series: Annotated[bool, Doc("Whether it is a time-series parameter.")] = field(default=False, kw_only=True)
    metadata: Annotated[
        dict[str, Any],
        Doc("A dictionary where you can store any parameter metadata. It is not used by pdag."),
    ] = field(
        default_factory=dict,
        kw_only=True,
    )

    def is_hydrated(self) -> bool:
        """Check if all required attributes are set."""
        return self.name_is_set()

    def name_is_set(self) -> bool:
        """Check if the name is set."""
        return isinstance(self._name, str)

    @property
    def name(self) -> str:
        """Property to get the name of the parameter.

        If you try to access it before it is set, it will raise a ValueError.
        """
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
        """Map a value from a unit interval `[0, 1]` to the parameter value space.

        This method should be implemented so that the uniform distribution in the unit interval
        corresponds to the "uniform" distribution in the parameter value space.

        !!! note
            We use the term "uniform" in a loose sense.
            We don't treat the resulting distribution as a probability distribution and
            the reason that the distribution should be as "uniform" as possible
            is to sample the parameter value space efficiently.
        """
        raise NotImplementedError

    def ref(
        self,
        *,
        previous: bool = False,
        next: bool = False,  # noqa: A002
        initial: bool = False,
        all_time_steps: bool = False,
    ) -> ParameterRef:
        """Create a reference to this parameter in the model definition."""
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
        """Linearly map a value from a unit interval `[0, 1]` to the parameter value space.

        0 corresponds to the lower bound and 1 corresponds to the upper bound.
        """
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


@dataclass
class PydanticParameter[M: BaseModel](ParameterABC[M]):
    """Parameter whose value is a Pydantic model."""

    type: ClassVar[str] = "pydantic"
    model: builtins.type[M]

    def get_type_hint(self) -> str:
        """Return the type hint for the Pydantic model."""
        return self.model.__name__

    def from_unit_interval(self, value: float) -> M:
        """Map a value from a unit interval `[0, 1]` to the Pydantic model.

        This method is not implemented because it depends on the specific model.
        """
        msg = "from_unit_interval is not implemented for PydanticParameter."
        raise NotImplementedError(msg)
