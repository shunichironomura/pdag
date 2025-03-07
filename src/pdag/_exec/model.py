from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Hashable, Iterable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Annotated, Any, Self, cast

import numpy.typing as npt
from typing_extensions import Doc

from pdag._core import ExecInfo, FunctionRelationship
from pdag._core.model import CoreModel
from pdag._core.parameter import ParameterABC
from pdag.utils import topological_sort

from .utils import parameter_id_to_parameter

_model_path_doc = """\
Path to the model. The root model is represented by an empty tuple.

A sub-model below defined by relationship name `rel_name` is represented by a tuple ("rel_name",)`.
"""

type ModelPathType = Annotated[tuple[str, ...], Doc(_model_path_doc)]
type NodePathType = Annotated[tuple[str, ...], Doc("Path to the node.")]


@dataclass(frozen=True, slots=True)
class NodeIdMixin:
    model_path: ModelPathType
    name: str

    @property
    def node_path(self) -> NodePathType:
        return (*self.model_path, self.name)

    @property
    def node_path_str(self) -> str:
        return ".".join(self.node_path)

    @classmethod
    def from_node_path(cls, node_path: NodePathType) -> Self:
        return cls(model_path=node_path[:-1], name=node_path[-1])

    @classmethod
    def from_node_path_str(cls, node_path_str: str) -> Self:
        return cls.from_node_path(tuple(node_path_str.split(".")))


@dataclass(frozen=True, slots=True)
class ParameterIdMixin(NodeIdMixin):
    @property
    def parmaeter_path(self) -> NodePathType:
        return self.node_path

    @property
    def parameter_path_str(self) -> str:
        return self.node_path_str

    @classmethod
    def from_parameter_path(cls, parameter_path: NodePathType) -> Self:
        return cls.from_node_path(parameter_path)

    @classmethod
    def from_parameter_path_str(cls, parameter_path_str: str) -> Self:
        return cls.from_node_path_str(parameter_path_str)


@dataclass(frozen=True, slots=True)
class StaticParameterId(ParameterIdMixin):
    model_path: ModelPathType
    name: str


@dataclass(frozen=True, slots=True)
class TimeSeriesParameterId(ParameterIdMixin):
    model_path: ModelPathType
    name: str
    time_step: int


@dataclass(frozen=True, slots=True)
class StaticRelationshipId(NodeIdMixin):
    model_path: ModelPathType
    name: str


@dataclass(frozen=True, slots=True)
class TimeSeriesRelationshipId(NodeIdMixin):
    model_path: ModelPathType
    name: str
    time_step: int


class ExecInfoType(StrEnum):
    N_TIME_STEPS = "n_time_steps"
    TIME = "time"

    @classmethod
    def from_exec_info(cls, exec_info: ExecInfo) -> Self:
        return cls(exec_info.attribute)


# Type aliases
type ParameterId = StaticParameterId | TimeSeriesParameterId
type FunctionRelationshipInputId = ExecInfoType | ParameterId | dict[Hashable, ParameterId]
type RelationshipId = StaticRelationshipId | TimeSeriesRelationshipId
type NodeId = ParameterId | RelationshipId


@dataclass(slots=True)
class ConnectorABC(ABC):
    @abstractmethod
    def iter_parameter_ids(self) -> Iterable[ParameterId]:
        raise NotImplementedError


@dataclass(slots=True)
class ScalarConnector(ConnectorABC):
    parameter_id: ParameterId

    def iter_parameter_ids(self) -> Iterable[ParameterId]:
        yield self.parameter_id


@dataclass(slots=True)
class MappingConnector(ConnectorABC):
    parameter_ids: dict[Hashable, ParameterId]

    def iter_parameter_ids(self) -> Iterable[ParameterId]:
        yield from self.parameter_ids.values()


@dataclass(slots=True)
class MappingListConnector(ConnectorABC):
    parameter_ids: list[dict[Hashable, ParameterId]]

    def iter_parameter_ids(self) -> Iterable[ParameterId]:
        for mapping in self.parameter_ids:
            yield from mapping.values()


@dataclass(slots=True)
class ArrayConnector(ConnectorABC):
    parameter_ids: npt.NDArray[ParameterId]  # type: ignore[type-var]

    def iter_parameter_ids(self) -> Iterable[ParameterId]:
        yield from self.parameter_ids.flat


@dataclass(slots=True)
class FunctionRelationshipInfo:
    function_relationship: FunctionRelationship[Any, Any]
    input_parameter_info: dict[str, ConnectorABC | ExecInfoType]
    output_parameter_info: tuple[ConnectorABC, ...]


@dataclass(slots=True)
class ExecutionModel:
    parameter_ids: set[ParameterId]
    # SubModelRelationships should be flattened into FunctionRelationships
    relationship_infos: dict[RelationshipId, FunctionRelationshipInfo]
    input_parameter_id_to_relationship_ids: dict[ParameterId, set[RelationshipId]]
    relationship_id_to_output_parameter_ids: dict[RelationshipId, set[ParameterId]]
    # parent model output to sub-model input / sub-model output to parent model input
    port_mapping: dict[ParameterId, ParameterId]

    _core_model: CoreModel = field(repr=False, compare=False, kw_only=True)

    n_time_steps: int | None = None

    # Derived attributes
    relationship_id_to_input_parameter_ids: dict[RelationshipId, set[ParameterId]] = field(
        init=False,
        repr=False,
        compare=False,
    )
    output_parameter_id_to_relationship_ids: dict[ParameterId, set[RelationshipId]] = field(
        init=False,
        repr=False,
        compare=False,
    )
    port_mapping_inverse: dict[ParameterId, ParameterId] = field(init=False, repr=False, compare=False)

    _topologically_sorted_node_ids: list[NodeId] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        relationship_id_to_input_parameter_ids_dd: defaultdict[RelationshipId, set[ParameterId]] = defaultdict(
            set,
        )
        for input_parameter_id, relationship_ids in self.input_parameter_id_to_relationship_ids.items():
            for relationship_id in relationship_ids:
                relationship_id_to_input_parameter_ids_dd[relationship_id].add(input_parameter_id)
        self.relationship_id_to_input_parameter_ids = dict(relationship_id_to_input_parameter_ids_dd)

        output_parameter_id_to_relationship_ids_dd: defaultdict[ParameterId, set[RelationshipId]] = defaultdict(
            set,
        )
        for relationship_id, output_parameter_ids in self.relationship_id_to_output_parameter_ids.items():
            for output_parameter_id in output_parameter_ids:
                output_parameter_id_to_relationship_ids_dd[output_parameter_id].add(relationship_id)
        self.output_parameter_id_to_relationship_ids = dict(output_parameter_id_to_relationship_ids_dd)

        self.port_mapping_inverse = {value: key for key, value in self.port_mapping.items()}

        # Calculate topological sort
        dependencies_dd: defaultdict[NodeId, set[NodeId]] = defaultdict(
            set,
            cast(dict[NodeId, set[NodeId]], self.input_parameter_id_to_relationship_ids)
            | cast(dict[NodeId, set[NodeId]], self.relationship_id_to_output_parameter_ids),
        )
        for src, dest in self.port_mapping.items():
            dependencies_dd[src].add(dest)
        dependencies = dict(dependencies_dd)
        # Sort nodes topologically
        self._topologically_sorted_node_ids = topological_sort(dependencies)

    def input_parameter_ids(self) -> set[ParameterId]:
        return {
            parameter_id
            for parameter_id in self.parameter_ids
            if parameter_id not in self.output_parameter_id_to_relationship_ids
            and parameter_id not in self.port_mapping_inverse
        }

    def input_parameters(self) -> dict[ParameterId, ParameterABC[Any]]:
        return {
            parameter_id: parameter_id_to_parameter(parameter_id, root_model=self._core_model)
            for parameter_id in self.input_parameter_ids()
        }

    @property
    def topologically_sorted_node_ids(self) -> list[NodeId]:
        return self._topologically_sorted_node_ids
