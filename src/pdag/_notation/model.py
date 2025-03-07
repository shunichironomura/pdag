from collections.abc import Hashable
from collections.abc import Mapping as MappingABC
from types import EllipsisType
from typing import Any, ClassVar, cast

from pdag._core import (
    CollectionABC,
    CoreModel,
    FunctionRelationship,
    Mapping,
    ParameterABC,
    ReferenceABC,
    RelationshipABC,
    SubModelRelationship,
)
from pdag.utils._multidef import MultiDef, MultiDefMeta, MultiDefStorage


def _function_relationship_multidef_storage_to_mapping(
    storage_name: str,
    storage: MultiDefStorage[FunctionRelationship[Any, Any]],
) -> Mapping[str | tuple[str, ...], FunctionRelationship[Any, Any]]:
    return Mapping(
        name=storage_name,
        mapping=dict(storage),  # type: ignore[arg-type]
    )


def _hydrate_name[T: CollectionABC[Hashable, ParameterABC[Any]] | ParameterABC[Any]](
    obj: T,
    name: str,
    *,
    force: bool = False,
) -> T:
    if not isinstance(obj.name, str) or force:
        obj.name = name
    return obj


class ModelMeta(MultiDefMeta):
    def __new__(
        metacls,  # noqa: N804
        name: str,
        bases: tuple[type[Any], ...],
        namespace: dict[str, Any],
    ) -> type:
        cls = super().__new__(metacls, name, bases, namespace)

        # Tell type checker that cls is essentially of type Model
        cls = cast(type["Model"], cls)

        cls.name = name

        # Add top-level collections
        cls.__pdag_collections__ = {
            collection_name: _hydrate_name(collection, collection_name)
            for collection_name, collection in namespace.items()
            if isinstance(collection, CollectionABC)
        }

        # Add MultiDefStorage instances (function relationships defined in loops) to __pdag_collections__
        cls.__pdag_collections__.update(
            {
                storage_name: _function_relationship_multidef_storage_to_mapping(storage_name, storage)
                for storage_name, storage in namespace.items()
                if isinstance(storage, MultiDefStorage)
            },
        )

        # Add top-level parameters
        cls.__pdag_parameters__ = {
            parameter_name: _hydrate_name(parameter, parameter_name)
            for parameter_name, parameter in namespace.items()
            if isinstance(parameter, ParameterABC)
        }

        # Add top-level relationships (function relationships at the top level)
        cls.__pdag_relationships__ = {}
        for relationship_name, relationship in namespace.items():
            if isinstance(relationship, RelationshipABC):
                cls.__pdag_relationships__[relationship_name] = relationship

        return cls


class Model(MultiDef, metaclass=ModelMeta):
    name: ClassVar[str]
    __pdag_parameters__: dict[str, ParameterABC[Any]]
    __pdag_relationships__: dict[str, RelationshipABC]
    __pdag_collections__: dict[str, CollectionABC[Any, Any]]

    @classmethod
    def parameters(cls) -> dict[str, ParameterABC[Any]]:
        return cls.__pdag_parameters__

    @classmethod
    def collections(cls) -> dict[str, CollectionABC[Any, Any]]:
        return cls.__pdag_collections__

    @classmethod
    def relationships(cls) -> dict[str, RelationshipABC]:
        return cls.__pdag_relationships__

    @classmethod
    def to_core_model(cls) -> CoreModel:
        return CoreModel(
            name=cls.__name__,
            parameters=cls.parameters(),
            collections=cls.collections(),
            relationships=cls.relationships(),
        )

    @classmethod
    def to_relationship(
        cls,
        /,
        name: str | EllipsisType,
        *,
        inputs: MappingABC[ReferenceABC, ReferenceABC],
        outputs: MappingABC[ReferenceABC, ReferenceABC],
        at_each_time_step: bool = False,
    ) -> SubModelRelationship:
        return SubModelRelationship(
            name=name,
            submodel_name=cls.name,
            inputs=dict(inputs),
            outputs=dict(outputs),
            _submodel=cls.to_core_model(),
            at_each_time_step=at_each_time_step,
        )
