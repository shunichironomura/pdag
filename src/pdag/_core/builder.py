from abc import ABC, abstractmethod
from collections.abc import Callable, Hashable
from dataclasses import dataclass, field
from types import EllipsisType
from typing import TYPE_CHECKING, Any

from pdag._core.collection import Array, CollectionABC, Mapping

from .parameter import ParameterABC
from .reference import (
    ArrayRef,
    ExecInfo,
    MappingRef,
    ParameterRef,
    ReferenceABC,
)
from .relationship import FunctionRelationship, RelationshipABC, SubModelRelationship

if TYPE_CHECKING:
    from .model import CoreModel


@dataclass
class RefBuilderABC(ABC):
    previous: bool = field(default=False, kw_only=True)
    next: bool = field(default=False, kw_only=True)
    initial: bool = field(default=False, kw_only=True)
    all_time_steps: bool = field(default=False, kw_only=True)

    @abstractmethod
    def build(self) -> ReferenceABC:
        raise NotImplementedError


@dataclass
class ParameterRefBuilder[T](RefBuilderABC):
    parameter: ParameterABC[T]

    def build(self) -> ParameterRef:
        return ParameterRef(
            name=self.parameter.name,
            previous=self.previous,
            next=self.next,
            initial=self.initial,
            all_time_steps=self.all_time_steps,
        )


@dataclass
class CollectionRefBuilder[K: Hashable](RefBuilderABC):
    collection: CollectionABC[Hashable, ParameterABC[Any] | RelationshipABC]

    key: str | tuple[str | EllipsisType, ...] | None = field(default=None)

    def build(self) -> MappingRef | ArrayRef:
        if isinstance(self.collection, Mapping):
            return MappingRef(
                name=self.collection.name,
                key=self.key,
                previous=self.previous,
                next=self.next,
                initial=self.initial,
                all_time_steps=self.all_time_steps,
            )
        if isinstance(self.collection, Array):
            return ArrayRef(
                name=self.collection.name,  # type: ignore[attr-defined]
                key=self.key,  # type: ignore[arg-type]
                previous=self.previous,
                next=self.next,
                initial=self.initial,
                all_time_steps=self.all_time_steps,
            )
        msg = "Collection must be either a Mapping or Array."
        raise ValueError(msg)


@dataclass
class FunctionRelationshipBuilder[**P, T]:
    name: str | EllipsisType
    at_each_time_step: bool = field(default=False, kw_only=True)
    inputs: dict[str, ReferenceABC | RefBuilderABC | ExecInfo] = field(kw_only=True)
    outputs: list[ReferenceABC | RefBuilderABC] = field(kw_only=True)
    function_body: str = field(kw_only=True)
    output_is_scalar: bool = field(kw_only=True)
    _function: Callable[P, T] | None = field(default=None, compare=False, kw_only=True)

    def build(self) -> FunctionRelationship[P, T]:
        return FunctionRelationship(
            name=self.name,
            inputs={name: ref.build() if isinstance(ref, RefBuilderABC) else ref for name, ref in self.inputs.items()},
            outputs=[ref.build() if isinstance(ref, RefBuilderABC) else ref for ref in self.outputs],
            function_body=self.function_body,
            at_each_time_step=self.at_each_time_step,
            output_is_scalar=self.output_is_scalar,
            _function=self._function,
        )


@dataclass
class SubModelRelationshipBuilder:
    name: str | EllipsisType
    at_each_time_step: bool = field(default=False, kw_only=True)
    submodel_name: str = field(kw_only=True)
    inputs: dict[ReferenceABC | RefBuilderABC, ReferenceABC | RefBuilderABC] = field(
        kw_only=True,
    )  # sub-model parameter ref -> parent model parameter ref
    outputs: dict[
        ReferenceABC | RefBuilderABC,
        ReferenceABC | RefBuilderABC,
    ] = field(kw_only=True)  # sub-model parameter ref -> parent model parameter ref
    _submodel: "CoreModel | None" = field(default=None, compare=False, kw_only=True)

    def build(self) -> SubModelRelationship:
        return SubModelRelationship(
            name=self.name,
            submodel_name=self.submodel_name,
            inputs={
                inner_ref.build() if isinstance(inner_ref, RefBuilderABC) else inner_ref: outer_ref.build()
                if isinstance(outer_ref, RefBuilderABC)
                else outer_ref
                for inner_ref, outer_ref in self.inputs.items()
            },
            outputs={
                inner_ref.build() if isinstance(inner_ref, RefBuilderABC) else inner_ref: outer_ref.build()
                if isinstance(outer_ref, RefBuilderABC)
                else outer_ref
                for inner_ref, outer_ref in self.outputs.items()
            },
            _submodel=self._submodel,
            at_each_time_step=self.at_each_time_step,
        )
