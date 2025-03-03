from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any, ClassVar, Self

from .utils import InitArgsRecorder


@dataclass(frozen=True)  # Frozen to be valid as a dictionary key
class ParameterRef(InitArgsRecorder):
    name: str
    previous: bool = field(default=False, kw_only=True)
    next: bool = field(default=False, kw_only=True)
    # Options to access time series data
    # TODO: Make this more flexible
    initial: bool = field(default=False, kw_only=True)
    all_time_steps: bool = field(default=False, kw_only=True)
    __init_args__: tuple[Any, ...] = field(init=False, compare=False, hash=False)
    __init_kwargs__: dict[str, Any] = field(init=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        if sum([self.previous, self.next, self.initial, self.all_time_steps]) > 1:
            msg = "Parameter reference cannot have more than one of previous, next, initial, or all_time_steps set."
            raise ValueError(msg)
        if not self.name.isidentifier():
            msg = "Parameter reference name must be a valid identifier."
            raise ValueError(msg)

    @property
    def normal(self) -> bool:
        return not any([self.previous, self.next, self.initial, self.all_time_steps])

    def __str__(self) -> str:
        s = self.name
        if self.previous:
            s += ".previous"
        if self.next:
            s += ".next"
        if self.initial:
            s += ".initial"
        if self.all_time_steps:
            s += ".all_time_steps"
        return s

    @classmethod
    def from_str(cls, s: str) -> Self:
        if ".previous" in s:
            name, _ = s.split(".previous")
            return cls(name=name, previous=True)
        if ".next" in s:
            name, _ = s.split(".next")
            return cls(name=name, next=True)
        if ".initial" in s:
            name, _ = s.split(".initial")
            return cls(name=name, initial=True)
        if ".all_time_steps" in s:
            name, _ = s.split(".all_time_steps")
            return cls(name=name, all_time_steps=True)
        return cls(name=s)


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
    categories: set[str]

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
    evaluated_at_each_time_step: bool = field(default=False, kw_only=True)

    @abstractmethod
    def is_hydrated(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def iter_input_parameter_refs(self) -> Iterable[ParameterRef]:
        raise NotImplementedError

    @abstractmethod
    def iter_output_parameter_refs(self) -> Iterable[ParameterRef]:
        raise NotImplementedError

    @property
    def includes_past(self) -> bool:
        return any(param_ref.previous for param_ref in self.iter_input_parameter_refs())

    @property
    def includes_future(self) -> bool:
        return any(param_ref.next for param_ref in self.iter_output_parameter_refs())


@dataclass
class FunctionRelationship[**P, T](RelationshipABC):
    type: ClassVar[str] = "function"
    name: str
    inputs: dict[str, ParameterRef]
    outputs: list[ParameterRef]
    function_body: str
    output_is_scalar: bool = field(kw_only=True)
    _function: Callable[P, T] | None = field(default=None, compare=False, kw_only=True)
    evaluated_at_each_time_step: bool = field(default=False, kw_only=True)

    def is_hydrated(self) -> bool:
        return self._function is not None

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        if self._function is None:
            msg = f"Function relationship {self.name} has not been hydrated."
            raise ValueError(msg)
        return self._function(*args, **kwargs)

    def iter_input_parameter_refs(self) -> Iterable[ParameterRef]:
        return self.inputs.values()

    def iter_output_parameter_refs(self) -> Iterable[ParameterRef]:
        return self.outputs


@dataclass
class SubModelRelationship(RelationshipABC):
    type: ClassVar[str] = "submodel"
    name: str
    submodel_name: str
    inputs: dict[ParameterRef, ParameterRef]  # sub-model parameter ref -> parent model parameter ref
    outputs: dict[ParameterRef, ParameterRef]  # sub-model parameter ref -> parent model parameter ref
    _submodel: "CoreModel | None" = field(default=None, compare=False, kw_only=True)
    evaluated_at_each_time_step: bool = field(default=False, kw_only=True)

    def is_hydrated(self) -> bool:
        return self._submodel is not None

    def iter_input_parameter_refs(self) -> Iterable[ParameterRef]:
        return self.inputs.values()

    def iter_output_parameter_refs(self) -> Iterable[ParameterRef]:
        return self.outputs.values()


@dataclass
class CoreModel:
    name: str
    parameters: dict[str, ParameterABC[Any]]
    collections: dict[str, ParameterCollectionABC]
    relationships: dict[str, RelationshipABC]

    def is_hydrated(self) -> bool:
        return (
            all(parameter.is_hydrated() for parameter in self.parameters.values())
            and all(collection.is_hydrated() for collection in self.collections.values())
            and all(relationship.is_hydrated() for relationship in self.relationships.values())
        )

    def is_dynamic(self) -> bool:
        return any(parameter.is_time_series for parameter in self.parameters.values())

    def get_parameter(self, parameter_ref: ParameterRef) -> ParameterABC[Any]:
        return self.parameters[parameter_ref.name]


@dataclass
class Module:
    pre_models: str
    models: list[CoreModel]  # Assuming topological order
    post_models: str

    def is_hydrated(self) -> bool:
        return all(model.is_hydrated() for model in self.models)
