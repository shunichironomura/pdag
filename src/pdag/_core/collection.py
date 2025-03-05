from abc import ABC, abstractmethod
from collections.abc import Hashable, Iterable
from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal, cast

from pdag.utils import InitArgsRecorder

from .parameter import ParameterABC
from .relationship import RelationshipABC


def _key_to_str(key: Any) -> str:
    if isinstance(key, tuple):
        return ", ".join(str(k) for k in key)
    return str(key)


@dataclass
class CollectionABC[K: Hashable, T: ParameterABC[Any] | RelationshipABC](ABC, InitArgsRecorder):
    type: ClassVar[str] = "collection"
    name: str
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

        self.name_elements()

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
            element.name = f"{self.name}[{_key_to_str(key)}]"

    def is_time_series(self) -> bool:
        if self.item_type == "parameter":
            return any(cast(ParameterABC[Any], parameter).is_time_series for parameter in self.values())
        msg = "Only collections of parameters can be time series."
        raise TypeError(msg)


@dataclass
class Mapping[K: str | tuple[str, ...], T: ParameterABC[Any] | RelationshipABC](CollectionABC[K, T]):
    type: ClassVar[str] = "mapping"
    name: str
    mapping: dict[K, T]

    def __getitem__(self, key: K) -> T:
        return self.mapping[key]

    def values(self) -> Iterable[T]:
        yield from self.mapping.values()

    def items(self) -> Iterable[tuple[K, T]]:
        yield from self.mapping.items()

    def keys(self) -> Iterable[K]:
        yield from self.mapping.keys()


type ElementOrArray[T] = list["ElementOrArray[T]"] | T


@dataclass
class Array[T: ParameterABC[Any] | RelationshipABC](CollectionABC[tuple[int, ...], T]):
    type: ClassVar[str] = "array"
    name: str
    array: list[ElementOrArray[T]]
    shape: tuple[int, ...] = field(init=False)

    def __post_init__(self) -> None:
        super().__post_init__()

        def _get_shape_recursive(
            elm_or_array: ElementOrArray[T],
            *,
            _shape: tuple[int, ...] = (),
        ) -> tuple[int, ...]:
            if isinstance(elm_or_array, ParameterABC | RelationshipABC):
                return _shape
            assert len(elm_or_array) == 0 or all(
                isinstance(element, ParameterABC) == isinstance(elm_or_array[0], ParameterABC)
                and isinstance(element, RelationshipABC) == isinstance(elm_or_array[0], RelationshipABC)
                for element in elm_or_array
            ), "All elements in an array must be of the same type."
            shape = (*_shape, len(elm_or_array))
            return _get_shape_recursive(elm_or_array[0], _shape=shape)

        self.shape = _get_shape_recursive(self.array)

    def __getitem__(self, key: tuple[int, ...]) -> T:
        element: ElementOrArray[T] = self.array
        for i in key:
            assert isinstance(element, list), (
                f"Key must be a tuple of integers matching the array shape. Got {key}, expected shape {self.shape}."
            )
            element = element[i]
        assert not isinstance(element, list), (
            f"Key must be a tuple of integers matching the array shape. Got {key}, expected shape {self.shape}."
        )
        return element

    def items(self) -> Iterable[tuple[tuple[int, ...], T]]:
        def _iter_parameters_with_index_recursive(
            array_or_param: ElementOrArray[T],
            index: tuple[int, ...],
        ) -> Iterable[tuple[tuple[int, ...], T]]:
            if not isinstance(array_or_param, list):
                yield index, array_or_param
            else:
                for i, element in enumerate(array_or_param):
                    yield from _iter_parameters_with_index_recursive(element, (*index, i))

        for i, element in enumerate(self.array):
            yield from _iter_parameters_with_index_recursive(element, (i,))


@dataclass
class ParameterCollectionABC[K: Hashable](CollectionABC[K, ParameterABC[Any]]):
    def __post_init__(self) -> None:
        super().__post_init__()

    @abstractmethod
    def iter_parameters(self) -> Iterable[ParameterABC[Any]]:
        raise NotImplementedError

    @abstractmethod
    def iter_parameter_names(self) -> Iterable[str]:
        raise NotImplementedError

    @abstractmethod
    def is_hydrated(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def name_parameters(self) -> None:
        raise NotImplementedError
