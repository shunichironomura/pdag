from collections import defaultdict, deque
from collections.abc import Mapping
from enum import StrEnum
from itertools import product
from typing import Any

from pdag._core import (
    CoreModel,
    ParameterABC,
    ParameterRef,
    FunctionRelationship,
    RelationshipABC,
)
from pdag.utils import topological_sort
from .model import StaticParameterIdentifier, TimeSeriesParameterIdentifier, ParameterIdentifier


def _to_identifiers(  # noqa: C901, PLR0912, PLR0913, PLR0915
    input_parameter_ref: ParameterRef,
    output_parameter_ref: ParameterRef,
    *,
    input_parameter_is_time_series: bool,
    output_parameter_is_time_series: bool,
    n_time_steps: int,
    relationship_includes_past: bool,
    relationship_includes_future: bool,
) -> list[tuple[ParameterIdentifier, ParameterIdentifier]]:
    if not input_parameter_is_time_series:
        input_identifier = StaticParameterIdentifier(name=input_parameter_ref.name)
        if not output_parameter_is_time_series:
            output_identifiers: list[ParameterIdentifier] = [StaticParameterIdentifier(name=output_parameter_ref.name)]
        elif output_parameter_ref.next:
            output_identifiers = [
                TimeSeriesParameterIdentifier(name=output_parameter_ref.name, time_step=time_step)
                for time_step in range(1, n_time_steps)
            ]
        elif output_parameter_ref.initial:
            output_identifiers = [TimeSeriesParameterIdentifier(name=output_parameter_ref.name, time_step=0)]
        elif output_parameter_ref.previous:
            msg = "Output parameter cannot have previous=True."
            raise ValueError(msg)
        elif output_parameter_ref.all_time_steps:
            output_identifiers = [
                TimeSeriesParameterIdentifier(name=output_parameter_ref.name, time_step=time_step)
                for time_step in range(n_time_steps)
            ]
        elif output_parameter_ref.normal:
            match (relationship_includes_past, relationship_includes_future):
                case (False, False):
                    time_steps = list(range(n_time_steps))
                case (True, False):
                    time_steps = list(range(1, n_time_steps))
                case (False, True):
                    time_steps = list(range(n_time_steps - 1))
                case _, _:
                    msg = "Invalid relationship configuration."
                    raise ValueError(msg)
            output_identifiers = [
                TimeSeriesParameterIdentifier(name=output_parameter_ref.name, time_step=time_step)
                for time_step in time_steps
            ]
        else:
            msg = "Invalid output parameter reference."
            raise ValueError(msg)
        return [(input_identifier, output_identifier) for output_identifier in output_identifiers]

    if not output_parameter_is_time_series:
        output_identifier = StaticParameterIdentifier(name=output_parameter_ref.name)
        if input_parameter_ref.all_time_steps:
            input_identifiers = [
                TimeSeriesParameterIdentifier(name=input_parameter_ref.name, time_step=time_step)
                for time_step in range(n_time_steps)
            ]
        else:
            msg = "Invalid input parameter reference."
            raise ValueError(msg)
        return [(input_identifier, output_identifier) for input_identifier in input_identifiers]

    # Both input and output are time series
    if (input_parameter_ref.previous and output_parameter_ref.normal) or (
        input_parameter_ref.normal and output_parameter_ref.next
    ):
        input_identifiers = [
            TimeSeriesParameterIdentifier(name=input_parameter_ref.name, time_step=time_step)
            for time_step in range(n_time_steps - 1)
        ]
        output_identifiers = [
            TimeSeriesParameterIdentifier(name=output_parameter_ref.name, time_step=time_step)
            for time_step in range(1, n_time_steps)
        ]
        return list(zip(input_identifiers, output_identifiers, strict=True))

    if input_parameter_ref.normal and output_parameter_ref.normal:
        match (relationship_includes_past, relationship_includes_future):
            case (False, False):
                time_steps = list(range(n_time_steps))
            case (True, False):
                time_steps = list(range(1, n_time_steps))
            case (False, True):
                time_steps = list(range(n_time_steps - 1))
            case _, _:
                msg = "Invalid relationship configuration."
                raise ValueError(msg)

        input_identifiers = [
            TimeSeriesParameterIdentifier(name=input_parameter_ref.name, time_step=time_step)
            for time_step in time_steps
        ]
        output_identifiers = [
            TimeSeriesParameterIdentifier(name=output_parameter_ref.name, time_step=time_step)
            for time_step in time_steps
        ]
        return list(zip(input_identifiers, output_identifiers, strict=True))

    msg = "Invalid input and output parameter references."
    raise ValueError(msg)


class RelationshipPhase(StrEnum):
    PRE_PROPAGATION = "pre_propagation"
    IN_PROPAGATION = "in_propagation"
    POST_PROPAGATION = "post_propagation"
    PRE_OR_POST_PROPAGATION = "pre_or_post_propagation"


def _exec_function_relationship_inner(
    relationship: FunctionRelationship[Any, Any],
    inputs: Mapping[ParameterRef, Any],
) -> dict[ParameterRef, Any]:
    assert relationship._function is not None

    function_inputs = {arg_name: inputs[relationship.inputs[arg_name]] for arg_name in relationship.inputs}
    function_outputs = relationship._function(**function_inputs)
    if relationship.output_is_scalar:
        return {relationship.outputs[0]: function_outputs}
    assert isinstance(function_outputs, tuple)
    return dict(zip(relationship.outputs, function_outputs, strict=True))


def _exec_relationship_inner(
    relationship: RelationshipABC,
    inputs: Mapping[ParameterRef, Any],
) -> dict[ParameterRef, Any]:
    if isinstance(relationship, FunctionRelationship):
        return _exec_function_relationship_inner(relationship, inputs)
    raise NotImplementedError


def _exec_relationship(  # noqa: C901, PLR0912
    relationship: RelationshipABC,
    inputs: Mapping[ParameterIdentifier, Any],
    output_to_include: ParameterIdentifier,
    parameters: Mapping[str, ParameterABC[Any]],
    *,
    n_time_steps: int,
) -> dict[ParameterIdentifier, Any]:
    """Execute a function relationship.

    `inputs` may contain extra parameters that are not required by the relationship.
    """
    corresponding_output_parameter_ref = next(
        output_parameter_ref
        for output_parameter_ref in relationship.iter_output_parameter_refs()
        if output_parameter_ref.name == output_to_include.name
    )

    if isinstance(output_to_include, TimeSeriesParameterIdentifier):
        if corresponding_output_parameter_ref.all_time_steps or corresponding_output_parameter_ref.initial:
            relationship_phase = RelationshipPhase.PRE_PROPAGATION
        else:
            relationship_phase = RelationshipPhase.IN_PROPAGATION
    else:
        relationship_phase = RelationshipPhase.PRE_OR_POST_PROPAGATION

    if relationship_phase == RelationshipPhase.IN_PROPAGATION:
        assert isinstance(output_to_include, TimeSeriesParameterIdentifier)
        relationship_time_step = (
            output_to_include.time_step - 1 if corresponding_output_parameter_ref.next else output_to_include.time_step
        )
        input_parameter_ref_to_identifier: dict[ParameterRef, ParameterIdentifier] = {}
        for parameter_ref in relationship.iter_input_parameter_refs():
            if parameters[parameter_ref.name].is_time_series:
                input_parameter_ref_to_identifier[parameter_ref] = TimeSeriesParameterIdentifier(
                    name=parameter_ref.name,
                    time_step=relationship_time_step - 1 if parameter_ref.previous else relationship_time_step,
                )
            else:
                input_parameter_ref_to_identifier[parameter_ref] = StaticParameterIdentifier(name=parameter_ref.name)
        input_values = {
            input_parameter_ref: inputs[input_parameter_ref_to_identifier[input_parameter_ref]]
            for input_parameter_ref in relationship.iter_input_parameter_refs()
        }
        relationship_outputs = _exec_relationship_inner(relationship, input_values)

        output_parameter_ref_to_identifier: dict[ParameterRef, ParameterIdentifier] = {}
        for parameter_ref in relationship.iter_output_parameter_refs():
            if parameters[parameter_ref.name].is_time_series:
                output_parameter_ref_to_identifier[parameter_ref] = TimeSeriesParameterIdentifier(
                    name=parameter_ref.name,
                    time_step=relationship_time_step + 1 if parameter_ref.next else relationship_time_step,
                )
            else:
                output_parameter_ref_to_identifier[parameter_ref] = StaticParameterIdentifier(name=parameter_ref.name)
        return {
            output_parameter_ref_to_identifier[parameter_ref]: relationship_outputs[parameter_ref]
            for parameter_ref in relationship.iter_output_parameter_refs()
        }

    input_values = {}
    for parameter_ref in relationship.iter_input_parameter_refs():
        if parameters[parameter_ref.name].is_time_series:
            assert parameter_ref.all_time_steps
            input_values[parameter_ref] = [
                inputs[TimeSeriesParameterIdentifier(name=parameter_ref.name, time_step=time_step)]
                for time_step in range(n_time_steps)
            ]
        else:
            input_values[parameter_ref] = inputs[StaticParameterIdentifier(name=parameter_ref.name)]
    relationship_outputs = _exec_relationship_inner(relationship, input_values)
    output_by_identifier: dict[ParameterIdentifier, Any] = {}
    for parameter_ref, output_value in relationship_outputs.items():
        if parameters[parameter_ref.name].is_time_series:
            if parameter_ref.all_time_steps:
                output_by_identifier.update(
                    {
                        TimeSeriesParameterIdentifier(name=parameter_ref.name, time_step=time_step): output_value[
                            time_step
                        ]
                        for time_step in range(n_time_steps)
                    },
                )
            else:
                assert parameter_ref.initial
                output_by_identifier[TimeSeriesParameterIdentifier(name=parameter_ref.name, time_step=0)] = output_value
        else:
            output_by_identifier[StaticParameterIdentifier(name=parameter_ref.name)] = output_value
    return output_by_identifier


def exec_core_model(  # noqa: C901, PLR0912
    core_model: CoreModel,
    inputs: Mapping[ParameterRef, Any],
    *,
    n_time_steps: int = 1,
) -> dict[ParameterIdentifier, Any]:
    parameter_identieifers: set[ParameterIdentifier] = {
        StaticParameterIdentifier(name=param_name)
        for param_name, parameter in core_model.parameters.items()
        if not parameter.is_time_series
    } | {
        TimeSeriesParameterIdentifier(name=param_name, time_step=time_step)
        for param_name, parameter in core_model.parameters.items()
        if parameter.is_time_series
        for time_step in range(n_time_steps)
    }
    identifier_to_relationship: dict[ParameterIdentifier, str] = {}

    relationships_without_inputs: set[RelationshipABC] = set()
    relationships_without_outputs: set[RelationshipABC] = set()
    dependencies_dd: defaultdict[ParameterIdentifier, set[ParameterIdentifier]] = defaultdict(set)  # input -> [output]
    for relationship in core_model.relationships.values():
        if not relationship.iter_input_parameter_refs():
            relationships_without_inputs.add(relationship)
            raise NotImplementedError
            continue
        if not relationship.iter_output_parameter_refs():
            relationships_without_outputs.add(relationship)
            raise NotImplementedError
            continue
        for input_parameter_ref, output_pararameter_ref in product(
            relationship.iter_input_parameter_refs(),
            relationship.iter_output_parameter_refs(),
        ):
            for input_identifier, output_identifier in _to_identifiers(
                input_parameter_ref,
                output_pararameter_ref,
                input_parameter_is_time_series=core_model.parameters[input_parameter_ref.name].is_time_series,
                output_parameter_is_time_series=core_model.parameters[output_pararameter_ref.name].is_time_series,
                n_time_steps=n_time_steps,
                relationship_includes_past=relationship.includes_past,
                relationship_includes_future=relationship.includes_future,
            ):
                dependencies_dd[input_identifier].add(output_identifier)
                identifier_to_relationship[output_identifier] = relationship.name
    dependencies = dict(dependencies_dd)
    # Topological sort
    sorted_identifiers = topological_sort(dependencies)

    assert set(sorted_identifiers) == parameter_identieifers, (
        f"Missing parameters: {parameter_identieifers - set(sorted_identifiers)}"
    )

    sorted_identifiers_queue = deque(sorted_identifiers)

    # TODO: The above operation can be cached and reused

    # Execute
    results: dict[ParameterIdentifier, Any] = {}
    while sorted_identifiers_queue:
        identifier = sorted_identifiers_queue.popleft()

        if identifier in results:
            continue

        if identifier not in identifier_to_relationship:
            # Get the value from the input
            for input_parameter_ref in inputs:
                if input_parameter_ref.name != identifier.name:
                    continue
                if isinstance(identifier, StaticParameterIdentifier) and input_parameter_ref.normal:
                    results[identifier] = inputs[input_parameter_ref]
                    break
                if (
                    isinstance(identifier, TimeSeriesParameterIdentifier)
                    and identifier.time_step == 0
                    and input_parameter_ref.initial
                ):
                    results[identifier] = inputs[input_parameter_ref]
                    break
                if isinstance(identifier, TimeSeriesParameterIdentifier) and input_parameter_ref.all_time_steps:
                    results[identifier] = inputs[input_parameter_ref][identifier.time_step]
                    break
            else:
                msg = f"Input value or a relationship to calculate {identifier} is missing."
                raise ValueError(msg)

        else:
            # Execute the relationship to get the value
            relationship = core_model.relationships[identifier_to_relationship[identifier]]
            results.update(
                _exec_relationship(
                    relationship,
                    results,
                    output_to_include=identifier,
                    parameters=core_model.parameters,
                    n_time_steps=n_time_steps,
                ),
            )

    return results
