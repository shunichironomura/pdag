from dataclasses import dataclass
from typing import Any

from .collection import CollectionABC
from .parameter import ParameterABC
from .reference import ParameterRef, ReferenceABC
from .relationship import RelationshipABC


@dataclass
class CoreModel:
    name: str
    parameters: dict[str, ParameterABC[Any]]
    relationships: dict[str, RelationshipABC]
    collections: dict[str, CollectionABC[Any, Any]]

    def is_hydrated(self) -> bool:
        return (
            all(parameter.is_hydrated() for parameter in self.parameters.values())
            and all(collection.is_hydrated() for collection in self.collections.values())
            and all(relationship.is_hydrated() for relationship in self.relationships.values())
        )

    def is_dynamic(self) -> bool:
        return any(parameter.is_time_series for parameter in self.parameters.values())

    def get_value(
        self,
        ref: ReferenceABC,
    ) -> ParameterABC[Any] | CollectionABC[Any, Any]:
        if isinstance(ref, ParameterRef):
            return self.get_parameter(ref)
        assert isinstance(ref.name, str)
        return self.parameters[ref.name]

    def get_parameter(self, ref: ParameterRef) -> ParameterABC[Any]:
        assert isinstance(ref.name, str)
        return self.parameters[ref.name]


@dataclass
class Module:
    pre_models: str
    models: list[CoreModel]  # Assuming topological order
    post_models: str

    def is_hydrated(self) -> bool:
        return all(model.is_hydrated() for model in self.models)
