from collections.abc import Hashable
from dataclasses import dataclass, field
from types import EllipsisType
from typing import Annotated, Any, Literal

from typing_extensions import Doc

from pdag._utils import InitArgsRecorder


@dataclass(frozen=True)  # Frozen to be valid as a dictionary key
class ReferenceABC(InitArgsRecorder):
    """Represents a reference to a parameter or collection in a model."""

    name: Annotated[str, Doc("Name of the parameter or collection.")]

    # For time-series access
    previous: bool = field(default=False, kw_only=True)
    next: bool = field(default=False, kw_only=True)
    initial: bool = field(default=False, kw_only=True)
    all_time_steps: bool = field(default=False, kw_only=True)

    __init_args__: tuple[Any, ...] = field(init=False, compare=False, hash=False)
    __init_kwargs__: dict[str, Any] = field(init=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        if sum([self.previous, self.next, self.initial, self.all_time_steps]) > 1:
            msg = "Reference cannot have more than one of previous, next, initial, or all_time_steps set."
            raise ValueError(msg)
        if not self.name.isidentifier():
            msg = "Reference name must be a valid identifier."
            raise ValueError(msg)

    @property
    def normal(self) -> bool:
        return not any([self.previous, self.next, self.initial, self.all_time_steps])


@dataclass(frozen=True)  # Frozen to be valid as a dictionary key
class ParameterRef(ReferenceABC):
    """Represents a reference to a parameter in a model."""


@dataclass(frozen=True)
class CollectionRef[K: Hashable](ReferenceABC):
    """Represents a reference to a collection in a model."""

    key: Annotated[K | None, Doc("Key to the collection. If None, it is a reference to the whole collection.")] = field(
        default=None,
    )


@dataclass(frozen=True)  # Frozen to be valid as a dictionary key
class MappingRef(CollectionRef[str | tuple[str | EllipsisType, ...]]):
    """Represents a reference to a mapping in a model."""


@dataclass(frozen=True)  # Frozen to be valid as a dictionary key
class ArrayRef(CollectionRef[tuple[int, ...]]):
    """Represents a reference to an array in a model."""


@dataclass(frozen=True)
class ExecInfo:
    """Represents the information available during the execution of a model."""

    attribute: Literal["n_time_steps", "time"]
