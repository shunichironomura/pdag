from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from types import EllipsisType
from typing import TYPE_CHECKING, ClassVar

from pdag.utils import InitArgsRecorder

from .reference import ExecInfo, ReferenceABC

if TYPE_CHECKING:
    from .model import CoreModel


@dataclass
class RelationshipABC(ABC, InitArgsRecorder):
    type: ClassVar[str] = "relationship"
    name: str | EllipsisType
    at_each_time_step: bool = field(default=False, kw_only=True)

    @abstractmethod
    def is_hydrated(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def iter_input_refs(self) -> Iterable[ReferenceABC | ExecInfo]:
        raise NotImplementedError

    @abstractmethod
    def iter_output_refs(self) -> Iterable[ReferenceABC]:
        raise NotImplementedError

    @property
    def includes_past(self) -> bool:
        return any(param_ref.previous for param_ref in self.iter_input_refs() if isinstance(param_ref, ReferenceABC))

    @property
    def includes_future(self) -> bool:
        return any(param_ref.next for param_ref in self.iter_output_refs())


@dataclass
class FunctionRelationship[**P, T](RelationshipABC):
    type: ClassVar[str] = "function"
    name: str | EllipsisType
    inputs: dict[str, ReferenceABC | ExecInfo]
    outputs: list[ReferenceABC]
    function_body: str
    output_is_scalar: bool = field(kw_only=True)
    _function: Callable[P, T] | None = field(default=None, compare=False, kw_only=True)

    def is_hydrated(self) -> bool:
        return self._function is not None

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        if self._function is None:
            msg = f"Function relationship {self.name} has not been hydrated."
            raise ValueError(msg)
        return self._function(*args, **kwargs)

    def iter_input_refs(self) -> Iterable[ReferenceABC | ExecInfo]:
        return self.inputs.values()

    def iter_output_refs(self) -> Iterable[ReferenceABC]:
        return self.outputs


@dataclass
class SubModelRelationship(RelationshipABC):
    type: ClassVar[str] = "submodel"
    name: str | EllipsisType
    submodel_name: str
    inputs: dict[
        ReferenceABC,
        ReferenceABC,
    ]  # sub-model parameter ref -> parent model parameter ref
    outputs: dict[
        ReferenceABC,
        ReferenceABC,
    ]  # sub-model parameter ref -> parent model parameter ref
    _submodel: "CoreModel | None" = field(default=None, compare=False, kw_only=True)

    def is_hydrated(self) -> bool:
        return self._submodel is not None

    def iter_input_refs(self) -> Iterable[ReferenceABC]:
        return self.inputs.values()

    def iter_output_refs(self) -> Iterable[ReferenceABC]:
        return self.outputs.values()

    @property
    def submodel(self) -> "CoreModel":
        if self._submodel is None:
            msg = f"Sub-model relationship {self.name} has not been hydrated."
            raise ValueError(msg)
        return self._submodel
