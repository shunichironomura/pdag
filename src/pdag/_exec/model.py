from dataclasses import dataclass

from pdag._core import RelationshipABC


@dataclass(frozen=True, slots=True)
class StaticParameterId:
    name: str


@dataclass(frozen=True, slots=True)
class TimeSeriesParameterId:
    name: str
    time_step: int


# Type aliases
type ParameterId = StaticParameterId | TimeSeriesParameterId
type RelationshipId = str
type NodeId = ParameterId | RelationshipId


@dataclass
class ExecutionModel:
    parameter_identifiers: set[ParameterId]
    relationships: set[RelationshipABC]
    input_parameter_id_to_relationship_ids: dict[ParameterId, set[RelationshipId]]
    relationship_id_to_output_parameter_ids: dict[RelationshipId, set[ParameterId]]
