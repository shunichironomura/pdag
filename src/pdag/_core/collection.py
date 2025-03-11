from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Hashable, Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Literal, cast

import numpy as np
import numpy.typing as npt

from pdag.utils import InitArgsRecorder

from .parameter import ParameterABC
from .reference import ArrayRef, CollectionRef, MappingRef
from .relationship import RelationshipABC

if TYPE_CHECKING:
    from types import EllipsisType

    from pdag._core.builder import CollectionRefBuilder


def key_to_str(key: Any, *, make_one_element_tuple_scalar: bool = False) -> str:
    if isinstance(key, tuple):
        if len(key) == 1 and make_one_element_tuple_scalar:
            return str(key[0])
        return ", ".join(str(k) for k in key)
    return str(key)


@dataclass
class CollectionABC[K: Hashable, T: ParameterABC[Any] | RelationshipABC](
    ABC,
    InitArgsRecorder,
):
    type: ClassVar[str] = "collection"
    name: str | EllipsisType
    item_type: Literal["parameter", "relationship"] = field(init=False)

    def __post_init__(self) -> None:
        for element in self.values():
            if isinstance(element, ParameterABC):
                self.item_type = "parameter"
                break
            if isinstance(element, RelationshipABC):
                self.item_type = "relationship"
                break
            msg = "Collection must contain only parameters or relationships."
            raise TypeError(msg)

    @abstractmethod
    def __getitem__(self, key: K) -> T:
        raise NotImplementedError

    @abstractmethod
    def items(self) -> Iterable[tuple[K, T]]:
        raise NotImplementedError

    def values(self) -> Iterable[T]:
        for _, element in self.items():  # noqa: PERF102
            yield element

    def keys(self) -> Iterable[K]:
        for key, _ in self.items():  # noqa: PERF102
            yield key

    def is_hydrated(self) -> bool:
        return all(elm.is_hydrated() for elm in self.values())

    def name_elements(self) -> None:
        for key, element in self.items():
            if isinstance(element.name, str):
                # Already named
                continue
            element.name = f"{self.name}[{key_to_str(key)}]"

    def is_time_series(self) -> bool:
        if self.item_type == "parameter":
            return any(cast(ParameterABC[Any], parameter).is_time_series for parameter in self.values())
        msg = "Only collections of parameters can be time series."
        raise TypeError(msg)

    @abstractmethod
    def ref(
        self,
        key: K | None = None,
        *,
        previous: bool = False,
        next: bool = False,  # noqa: A002
        initial: bool = False,
        all_time_steps: bool = False,
    ) -> CollectionRef[K] | CollectionRefBuilder[K]:
        raise NotImplementedError


@dataclass
class Mapping[K: str | tuple[str, ...], T: ParameterABC[Any] | RelationshipABC](
    CollectionABC[K, T],
):
    type: ClassVar[str] = "mapping"
    name: str | EllipsisType
    mapping: dict[K, T]

    def __getitem__(self, key: K) -> T:
        return self.mapping[key]

    def values(self) -> Iterable[T]:
        yield from self.mapping.values()

    def items(self) -> Iterable[tuple[K, T]]:
        yield from self.mapping.items()

    def keys(self) -> Iterable[K]:
        yield from self.mapping.keys()

    def ref(  # type: ignore[override]
        self,
        key: str | tuple[str | EllipsisType, ...] | None = None,
        *,
        previous: bool = False,
        next: bool = False,  # noqa: A002
        initial: bool = False,
        all_time_steps: bool = False,
    ) -> MappingRef | CollectionRefBuilder[str | tuple[str | EllipsisType, ...]]:
        if isinstance(self.name, str):
            return MappingRef(
                name=self.name,
                key=key,
                previous=previous,
                next=next,
                initial=initial,
                all_time_steps=all_time_steps,
            )

        from .builder import CollectionRefBuilder

        return CollectionRefBuilder(
            collection=self,  # type: ignore[arg-type]
            previous=previous,
            next=next,
            initial=initial,
            all_time_steps=all_time_steps,
        )


@dataclass
class Array[T: ParameterABC[Any] | RelationshipABC](CollectionABC[tuple[int, ...], T]):
    type: ClassVar[str] = "array"
    name: str | EllipsisType
    array: npt.NDArray[T]  # type: ignore[type-var]

    @property
    def shape(self) -> tuple[int, ...]:
        return self.array.shape

    def __post_init__(self) -> None:
        super().__post_init__()

    def __getitem__(self, key: tuple[int, ...]) -> T:
        return self.array[key]  # type: ignore[no-any-return]

    def items(self) -> Iterable[tuple[tuple[int, ...], T]]:
        yield from np.ndenumerate(self.array)

    def ref(
        self,
        key: tuple[int, ...] | None = None,
        *,
        previous: bool = False,
        next: bool = False,  # noqa: A002
        initial: bool = False,
        all_time_steps: bool = False,
    ) -> ArrayRef | CollectionRefBuilder[tuple[int, ...]]:
        if isinstance(self.name, str):
            return ArrayRef(
                name=self.name,
                key=key,
                previous=previous,
                next=next,
                initial=initial,
                all_time_steps=all_time_steps,
            )

        from .builder import CollectionRefBuilder

        return CollectionRefBuilder(
            collection=self,  # type: ignore[arg-type]
            key=key,  # type: ignore[arg-type]
            previous=previous,
            next=next,
            initial=initial,
            all_time_steps=all_time_steps,
        )
