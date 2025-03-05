from collections.abc import Mapping as MappingABC
from types import EllipsisType
from typing import Any, ClassVar, cast

from pdag._core import (
    CollectionABC,
    CollectionRef,
    CoreModel,
    FunctionRelationship,
    Mapping,
    ParameterABC,
    ParameterRef,
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
        # TODO: Collect function relationship mappings
        cls.__pdag_collections__ = {
            collection_name: collection
            for collection_name, collection in namespace.items()
            if isinstance(collection, CollectionABC)
        }
        cls.__pdag_collections__.update(
            {
                storage_name: _function_relationship_multidef_storage_to_mapping(storage_name, storage)
                for storage_name, storage in namespace.items()
                if isinstance(storage, MultiDefStorage)
            },
        )
        cls.__pdag_parameters__ = {
            parameter_name: parameter
            for parameter_name, parameter in namespace.items()
            if isinstance(parameter, ParameterABC)
        }

        cls.__pdag_relationships__ = {}
        for relationship_name, relationship in namespace.items():
            if isinstance(relationship, RelationshipABC):
                for output_ref in relationship.iter_output_refs():
                    assert isinstance(output_ref.name, str)
                    if isinstance(output_ref, ParameterRef):
                        output_param_or_col: CollectionABC[Any, Any] | ParameterABC[Any] = cls.__pdag_parameters__[
                            output_ref.name
                        ]
                    elif isinstance(output_ref, CollectionRef):
                        output_param_or_col = cls.__pdag_collections__[output_ref.name]
                    else:
                        msg = f"Output reference {output_ref} is not a ParameterRef or CollectionRef"
                        raise TypeError(msg)
                    if output_param_or_col.is_time_series and (output_ref.normal or output_ref.next):
                        relationship.evaluated_at_each_time_step = True
                        break
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
    ) -> SubModelRelationship:
        return SubModelRelationship(
            name=name,
            submodel_name=cls.name,
            inputs=dict(inputs),
            outputs=dict(outputs),
            _submodel=cls.to_core_model(),
        )
