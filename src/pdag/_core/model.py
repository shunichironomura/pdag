from collections.abc import Iterable
from dataclasses import dataclass
from typing import Annotated, Any

from typing_extensions import Doc

from .collection import CollectionABC
from .parameter import ParameterABC
from .reference import CollectionRef, ParameterRef, ReferenceABC
from .relationship import RelationshipABC


@dataclass
class CoreModel:
    name: Annotated[str, Doc("Name of the model.")]
    parameters: Annotated[
        dict[str, ParameterABC[Any]],
        Doc(
            "Mapping of parameter names to parameters. Parameters contained in collections are not included.",
        ),
    ]
    relationships: Annotated[
        dict[str, RelationshipABC],
        Doc(
            "Mapping of relationship names to relationships. Relationships contained in collections are not included.",
        ),
    ]
    collections: Annotated[
        dict[str, CollectionABC[Any, Any]],
        Doc("Mapping of collection names to collections."),
    ]

    def is_hydrated(self) -> bool:
        """Check if all parameters, collections, and relationships are hydrated."""
        return (
            all(parameter.is_hydrated() for parameter in self.parameters.values())
            and all(collection.is_hydrated() for collection in self.collections.values())
            and all(relationship.is_hydrated() for relationship in self.relationships.values())
        )

    def is_dynamic(self) -> bool:
        """Check if any parameter is dynamic."""
        return any(parameter.is_time_series for parameter in self.parameters.values())

    def iter_all_parameters(self) -> Iterable[ParameterABC[Any]]:
        """Yield all parameters contained in the model, including those in collections.

        It does NOT include parameters in sub-models.
        """
        yield from self.parameters.values()
        for collection in self.collections.values():
            if collection.item_type == "parameter":
                yield from collection.values()

    def iter_all_relationships(self) -> Iterable[RelationshipABC]:
        """Yield all relationships contained in the model, including those in collections.

        It does NOT include relationships in sub-models.
        """
        yield from self.relationships.values()
        for collection in self.collections.values():
            if collection.item_type == "relationship":
                yield from collection.values()

    def get_object(
        self,
        ref: ReferenceABC,
    ) -> ParameterABC[Any] | CollectionABC[Any, Any]:
        if isinstance(ref, ParameterRef):
            return self.get_parameter(ref)
        if isinstance(ref, CollectionRef):
            return self.get_collection(ref)
        msg = f"Reference type {type(ref)} is not supported."
        raise TypeError(msg)

    def get_parameter(self, ref: ParameterRef) -> ParameterABC[Any]:
        assert isinstance(ref.name, str)
        return self.parameters[ref.name]

    def get_collection(self, ref: CollectionRef[Any]) -> CollectionABC[Any, Any]:
        assert isinstance(ref.name, str)
        return self.collections[ref.name]


@dataclass
class Module:
    pre_models: str
    models: list[CoreModel]  # Assuming topological order
    post_models: str

    def is_hydrated(self) -> bool:
        return all(model.is_hydrated() for model in self.models)
