from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Hashable, Iterable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Annotated, Any, Self

import numpy.typing as npt
from typing_extensions import Doc

from pdag._core import ExecInfo, FunctionRelationship

_model_path_doc = """\
Path to the model. The root model is represented by an empty tuple.

A sub-model below defined by relationship name `rel_name` is represented by a tuple ("rel_name",)`.
"""

type ModelPathType = Annotated[tuple[str, ...], Doc(_model_path_doc)]


@dataclass(frozen=True, slots=True)
class StaticParameterId:
    model_path: Annotated[tuple[str, ...], Doc(_model_path_doc)]
    name: str


@dataclass(frozen=True, slots=True)
class TimeSeriesParameterId:
    model_path: Annotated[tuple[str, ...], Doc(_model_path_doc)]
    name: str
    time_step: int


@dataclass(frozen=True, slots=True)
class StaticRelationshipId:
    model_path: Annotated[tuple[str, ...], Doc(_model_path_doc)]
    name: str


@dataclass(frozen=True, slots=True)
class TimeSeriesRelationshipId:
    model_path: Annotated[tuple[str, ...], Doc(_model_path_doc)]
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


type ElementOrArray[T] = list["ElementOrArray[T]"] | T


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


@dataclass
class ExecutionModel:
    parameter_ids: set[ParameterId]
    # SubModelRelationships should be flattened into FunctionRelationships
    relationship_infos: dict[RelationshipId, FunctionRelationshipInfo]
    input_parameter_id_to_relationship_ids: dict[ParameterId, set[RelationshipId]]
    relationship_id_to_output_parameter_ids: dict[RelationshipId, set[ParameterId]]
    # parent model output to sub-model input / sub-model output to parent model input
    port_mapping: dict[ParameterId, ParameterId]

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

    def input_parameter_ids(self) -> set[ParameterId]:
        return {
            parameter_id
            for parameter_id in self.parameter_ids
            if parameter_id not in self.output_parameter_id_to_relationship_ids
            and parameter_id not in self.port_mapping_inverse
        }
