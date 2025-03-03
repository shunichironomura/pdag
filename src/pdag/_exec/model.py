from dataclasses import dataclass, field
from typing import Any

from pdag._core import FunctionRelationship
from collections import defaultdict


@dataclass(frozen=True, slots=True)
class StaticParameterId:
    name: str


@dataclass(frozen=True, slots=True)
class TimeSeriesParameterId:
    name: str
    time_step: int


type ParameterId = StaticParameterId | TimeSeriesParameterId


@dataclass(frozen=True, slots=True)
class AbsoluteStaticParameterId:
    model_name: str
    name: str


@dataclass(frozen=True, slots=True)
class AbsoluteTimeSeriesParameterId:
    model_name: str
    name: str
    time_step: int


@dataclass(frozen=True, slots=True)
class AbsoluteStaticRelationshipId:
    model_name: str
    name: str


@dataclass(frozen=True, slots=True)
class AbsoluteTimeSeriesRelationshipId:
    model_name: str
    name: str
    time_step: int


# Type aliases
type AbsoluteParameterId = AbsoluteStaticParameterId | AbsoluteTimeSeriesParameterId
type AbsoluteRelationshipId = AbsoluteStaticRelationshipId | AbsoluteTimeSeriesRelationshipId
type NodeId = AbsoluteParameterId | AbsoluteRelationshipId


@dataclass
class ExecutionModel:
    parameter_ids: set[AbsoluteParameterId]
    # SubModelRelationships should be flattened into FunctionRelationships
    relationships: list[FunctionRelationship[Any, Any]]
    input_parameter_id_to_relationship_ids: dict[AbsoluteParameterId, set[AbsoluteRelationshipId]]
    relationship_id_to_output_parameter_ids: dict[AbsoluteRelationshipId, set[AbsoluteParameterId]]
    # parent model output to sub-model input / sub-model output to parent model input
    port_mapping: dict[AbsoluteParameterId, AbsoluteParameterId]

    # Derived attributes
    relationship_id_to_input_parameter_ids: dict[AbsoluteRelationshipId, set[AbsoluteParameterId]] = field(
        init=False, repr=False, compare=False
    )
    output_parameter_id_to_relationship_ids: dict[AbsoluteParameterId, set[AbsoluteRelationshipId]] = field(
        init=False, repr=False, compare=False
    )
    port_mapping_inverse: dict[AbsoluteParameterId, AbsoluteParameterId] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        relationship_id_to_input_parameter_ids_dd: defaultdict[AbsoluteRelationshipId, set[AbsoluteParameterId]] = (
            defaultdict(set)
        )
        for input_parameter_id, relationship_ids in self.input_parameter_id_to_relationship_ids.items():
            for relationship_id in relationship_ids:
                relationship_id_to_input_parameter_ids_dd[relationship_id].add(input_parameter_id)
        self.relationship_id_to_input_parameter_ids = dict(relationship_id_to_input_parameter_ids_dd)

        output_parameter_id_to_relationship_ids_dd: defaultdict[AbsoluteParameterId, set[AbsoluteRelationshipId]] = (
            defaultdict(set)
        )
        for relationship_id, output_parameter_ids in self.relationship_id_to_output_parameter_ids.items():
            for output_parameter_id in output_parameter_ids:
                output_parameter_id_to_relationship_ids_dd[output_parameter_id].add(relationship_id)
        self.port_mapping_inverse = {value: key for key, value in self.port_mapping.items()}
