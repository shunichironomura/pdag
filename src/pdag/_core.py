from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, ClassVar

from .utils import InitArgsRecorder


@dataclass
class ParameterABC[T](InitArgsRecorder, ABC):
    type: ClassVar[str] = "base"
    name: str
    is_time_series: bool = field(default=False, kw_only=True)

    @abstractmethod
    def is_hydrated(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_type_hint(self) -> str:
        raise NotImplementedError


@dataclass
class RealParameter(ParameterABC[float]):
    type: ClassVar[str] = "real"
    unit: str | None = None
    lower_bound: float | None = None
    upper_bound: float | None = None

    def is_hydrated(self) -> bool:
        return True

    def get_type_hint(self) -> str:
        return "float"


@dataclass
class CategoricalParameter(ParameterABC[str]):
    type: ClassVar[str] = "categorical"
    categories: frozenset[str]

    def is_hydrated(self) -> bool:
        return True

    def get_type_hint(self) -> str:
        return f"Literal[{', '.join(repr(category) for category in self.categories)}]"


@dataclass
class ParameterCollectionABC(ABC, InitArgsRecorder):
    type: ClassVar[str] = "collection"
    name: str

    @abstractmethod
    def iter_parameter_names(self) -> Iterable[str]:
        raise NotImplementedError

    @abstractmethod
    def is_hydrated(self) -> bool:
        raise NotImplementedError


@dataclass
class ParameterMapping(ParameterCollectionABC):
    type: ClassVar[str] = "mapping"
    name: str
    mapping: dict[str, str]

    def iter_parameter_names(self) -> Iterable[str]:
        return self.mapping.values()

    def is_hydrated(self) -> bool:
        return True


type StrArrayOrStr = list["StrArrayOrStr"] | str


@dataclass
class ParameterArray(ParameterCollectionABC):
    type: ClassVar[str] = "array"
    name: str
    shape: tuple[int, ...]
    array: list[StrArrayOrStr]

    def iter_parameter_names(self) -> Iterable[str]:
        def _iter_parameter_names(array_or_str: StrArrayOrStr) -> Iterable[str]:
            if isinstance(array_or_str, str):
                yield array_or_str
            else:
                for element in array_or_str:
                    yield from _iter_parameter_names(element)

        for element in self.array:
            yield from _iter_parameter_names(element)

    def is_hydrated(self) -> bool:
        return True


@dataclass
class RelationshipABC(ABC, InitArgsRecorder):
    type: ClassVar[str] = "relationship"
    name: str

    @abstractmethod
    def is_hydrated(self) -> bool:
        raise NotImplementedError


@dataclass
class FunctionRelationship(RelationshipABC):
    type: ClassVar[str] = "function"
    name: str
    inputs: Mapping[str, str]
    outputs: Sequence[str]
    function_body: str
    output_is_scalar: bool = field(kw_only=True)
    _function: Callable[..., Any] | None = field(default=None, compare=False)

    def is_hydrated(self) -> bool:
        return self._function is not None


@dataclass
class SubModelRelationship(RelationshipABC):
    type: ClassVar[str] = "submodel"
    name: str
    submodel_name: str
    inputs: Mapping[str, str]
    outputs: Mapping[str, str]
    _submodel: "CoreModel | None" = field(default=None, compare=False)

    def is_hydrated(self) -> bool:
        return self._submodel is not None


@dataclass
class CoreModel:
    name: str
    parameters: dict[str, ParameterABC[Any]]
    collections: dict[str, ParameterCollectionABC]
    relationships: dict[str, RelationshipABC]

    def is_hydrated(self) -> bool:
        return (
            all(node.is_hydrated() for node in self.parameters.values())
            and all(collection.is_hydrated() for collection in self.collections.values())
            and all(relationship.is_hydrated() for relationship in self.relationships.values())
        )


@dataclass
class Module:
    pre_models: str
    models: list[CoreModel]
    post_models: str

    def is_hydrated(self) -> bool:
        return all(model.is_hydrated() for model in self.models)
