from collections import defaultdict, deque
from collections.abc import Mapping
from typing import Any, cast

from pdag.utils import topological_sort

from .model import (
    AbsoluteParameterId,
    AbsoluteStaticParameterId,
    AbsoluteStaticRelationshipId,
    AbsoluteTimeSeriesParameterId,
    AbsoluteTimeSeriesRelationshipId,
    ExecutionModel,
    NodeId,
)


def execute_exec_model(  # noqa: C901, PLR0912
    exec_model: ExecutionModel,
    inputs: Mapping[AbsoluteParameterId, Any],
) -> dict[AbsoluteParameterId, Any]:
    # TODO: Exec only part of the model
    # Calculate dependencies
    dependencies_dd: defaultdict[NodeId, set[NodeId]] = defaultdict(
        set,
        cast(dict[NodeId, set[NodeId]], exec_model.input_parameter_id_to_relationship_ids)
        | cast(dict[NodeId, set[NodeId]], exec_model.relationship_id_to_output_parameter_ids),
    )
    for src, dest in exec_model.port_mapping.items():
        dependencies_dd[src].add(dest)
    dependencies = dict(dependencies_dd)
    # Sort nodes topologically
    sorted_nodes = topological_sort(dependencies)

    sorted_nodes_queue = deque(sorted_nodes)
    results: dict[AbsoluteParameterId, Any] = {}
    while sorted_nodes_queue:
        node_id = sorted_nodes_queue.popleft()

        if node_id in results:
            continue

        if isinstance(node_id, AbsoluteStaticParameterId | AbsoluteTimeSeriesParameterId):
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

        if isinstance(node_id, AbsoluteStaticRelationshipId | AbsoluteTimeSeriesRelationshipId):
            relationship_info = exec_model.relationship_infos[node_id]
            input_values: dict[str, Any] = {}
            for input_arg_name, input_parameter_id in relationship_info.input_parameter_ids.items():
                if isinstance(input_parameter_id, tuple):
                    input_values[input_arg_name] = tuple(
                        results[input_param_id] for input_param_id in input_parameter_id
                    )
                else:
                    input_values[input_arg_name] = results[input_parameter_id]

            output_values = relationship_info.function_relationship(**input_values)

            if relationship_info.function_relationship.output_is_scalar:
                output_values = (output_values,)
            for output_parameter_id, output_value in zip(
                relationship_info.output_parameter_ids,
                output_values,
                strict=True,
            ):
                if isinstance(output_parameter_id, tuple):
                    results.update(zip(output_parameter_id, output_value, strict=True))
                else:
                    results[output_parameter_id] = output_value

    return results
