from collections import deque
from collections.abc import Mapping
from typing import Any

import numpy as np

from .model import (
    ArrayConnector,
    ExecInfoType,
    ExecutionModel,
    MappingConnector,
    MappingListConnector,
    ParameterId,
    RelationshipId,
    ScalarConnector,
    StaticParameterId,
    StaticRelationshipId,
    TimeSeriesParameterId,
    TimeSeriesRelationshipId,
)


def _get_exec_info_value(
    exec_model: ExecutionModel,
    exec_info_type: ExecInfoType,
    relationship_id: RelationshipId,
) -> Any:
    match exec_info_type:
        case ExecInfoType.N_TIME_STEPS:
            return exec_model.n_time_steps
        case ExecInfoType.TIME:
            if isinstance(relationship_id, TimeSeriesRelationshipId):
                return relationship_id.time_step
            msg = f"Node {relationship_id} is not a TimeSeriesRelationshipId"
            raise ValueError(msg)


def execute_exec_model(  # noqa: C901, PLR0912, PLR0915
    exec_model: ExecutionModel,
    inputs: Mapping[ParameterId, Any],
) -> dict[ParameterId, Any]:
    # TODO: Exec only part of the model (in which case you need to sort the nodes again?)
    sorted_nodes_queue = deque(exec_model.topologically_sorted_node_ids)
    results: dict[ParameterId, Any] = {}
    while sorted_nodes_queue:
        node_id = sorted_nodes_queue.popleft()

        if node_id in results:
            continue

        if isinstance(node_id, StaticParameterId | TimeSeriesParameterId):
            if node_id in inputs:
                results[node_id] = inputs[node_id]
                continue
            if node_id in exec_model.port_mapping_inverse:
                parent_node_id = exec_model.port_mapping_inverse[node_id]
                if parent_node_id in inputs:
                    results[node_id] = inputs[parent_node_id]
                    continue
                if parent_node_id in results:
                    results[node_id] = results[parent_node_id]
                    continue
                msg = f"Parent node {parent_node_id} not in results"
                raise ValueError(msg)
            msg = f"Node {node_id} not in inputs or port_mapping"
            raise ValueError(msg)

        if isinstance(node_id, StaticRelationshipId | TimeSeriesRelationshipId):
            relationship_info = exec_model.relationship_infos[node_id]

            input_values: dict[str, Any] = {}
            for input_arg_name, connector_or_exec_info in relationship_info.input_parameter_info.items():
                if isinstance(connector_or_exec_info, ExecInfoType):
                    input_values[input_arg_name] = _get_exec_info_value(
                        exec_model,
                        connector_or_exec_info,
                        node_id,
                    )
                    continue
                if isinstance(connector_or_exec_info, ScalarConnector):
                    input_values[input_arg_name] = results[connector_or_exec_info.parameter_id]
                    continue
                if isinstance(connector_or_exec_info, MappingConnector):
                    input_values[input_arg_name] = {
                        key: results[param_id] for key, param_id in connector_or_exec_info.parameter_ids.items()
                    }
                    continue
                if isinstance(connector_or_exec_info, MappingListConnector):
                    input_values[input_arg_name] = [
                        {key: results[param_id] for key, param_id in mapping.items()}
                        for mapping in connector_or_exec_info.parameter_ids
                    ]
                    continue
                if isinstance(connector_or_exec_info, ArrayConnector):
                    value_array = np.empty(connector_or_exec_info.parameter_ids.shape, dtype=object)
                    for index, param_id in np.ndenumerate(connector_or_exec_info.parameter_ids):
                        value_array[index] = results[param_id]
                    input_values[input_arg_name] = value_array.tolist()
                    continue
                msg = f"Connector type {type(connector_or_exec_info)} is not supported."
                raise TypeError(msg)

            output_values = relationship_info.function_relationship(**input_values)

            if relationship_info.function_relationship.output_is_scalar:
                output_values = (output_values,)
            for connector, output_value in zip(
                relationship_info.output_parameter_info,
                output_values,
                strict=True,
            ):
                if isinstance(connector, ScalarConnector):
                    results[connector.parameter_id] = output_value
                    continue
                if isinstance(connector, MappingConnector):
                    for key, param_id in connector.parameter_ids.items():
                        results[param_id] = output_value[key]
                    continue
                if isinstance(connector, MappingListConnector):
                    for mapping, output_value_item in zip(connector.parameter_ids, output_value, strict=True):
                        for key, param_id in mapping.items():
                            results[param_id] = output_value_item[key]
                    continue
                if isinstance(connector, ArrayConnector):
                    for index, param_id in np.ndenumerate(connector.parameter_ids):
                        results[param_id] = np.asarray(output_value, dtype=object)[index]
                    continue
                msg = f"Connector type {type(connector)} is not supported."
                raise TypeError(msg)

    return results
