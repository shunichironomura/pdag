from collections import defaultdict
from collections.abc import Iterable
from typing import Any
from pdag._core import CoreModel, FunctionRelationship, SubModelRelationship, ParameterABC
from .model import (
    ExecutionModel,
    AbsoluteTimeSeriesParameterId,
    AbsoluteStaticParameterId,
    AbsoluteParameterId,
    AbsoluteStaticRelationshipId,
    AbsoluteTimeSeriesRelationshipId,
    AbsoluteRelationshipId,
)
from pdag.utils import merge_two_set_dicts


def _iter_submodels_recursively(
    core_model: CoreModel,
    *,
    include_self: bool = False,
) -> Iterable[CoreModel]:
    assert core_model.is_hydrated(), "CoreModel must be hydrated."
    if include_self:
        yield core_model
    for relationship in core_model.relationships.values():
        if isinstance(relationship, SubModelRelationship):
            assert relationship._submodel is not None, "SubModelRelationship must be hydrated."
            yield relationship._submodel
            yield from _iter_submodels_recursively(relationship._submodel)


def _iter_function_relationships_recursively(
    core_model: CoreModel,
) -> Iterable[tuple[CoreModel, FunctionRelationship[Any, Any]]]:
    """Iterate over all function relationships in the core model.

    Yields tuples of the form (submodel, relationship).
    """
    assert core_model.is_hydrated(), "CoreModel must be hydrated."
    for submodel in _iter_submodels_recursively(core_model, include_self=True):
        for relationship in submodel.relationships.values():
            if isinstance(relationship, FunctionRelationship):
                yield submodel, relationship


def _iter_submodel_relationships_recursively(
    core_model: CoreModel,
) -> Iterable[tuple[CoreModel, SubModelRelationship]]:
    """Iterate over all submodel relationships in the core model.

    Yields tuples of the form (submodel, relationship).
    """
    assert core_model.is_hydrated(), "CoreModel must be hydrated."
    for submodel in _iter_submodels_recursively(core_model, include_self=True):
        for relationship in submodel.relationships.values():
            if isinstance(relationship, SubModelRelationship):
                yield submodel, relationship


def _iter_parameters_recursively(
    core_model: CoreModel,
) -> Iterable[tuple[CoreModel, ParameterABC[Any]]]:
    """Iterate over all parameters in the core model.

    Yields tuples of the form (submodel, parameter).
    """
    assert core_model.is_hydrated(), "CoreModel must be hydrated."
    for submodel in _iter_submodels_recursively(core_model, include_self=True):
        for parameter in submodel.parameters.values():
            yield submodel, parameter


def _calculate_dependencies_of_time_series_function_relationship(
    relationship: FunctionRelationship[Any, Any],
    *,
    core_model: CoreModel,
    n_time_steps: int,
) -> tuple[
    dict[AbsoluteParameterId, set[AbsoluteRelationshipId]],  # input_parameter_id_to_relationship_ids
    dict[AbsoluteRelationshipId, set[AbsoluteParameterId]],  # relationship_id_to_output_parameter_ids
]:
    assert relationship.evaluated_at_each_time_step, (
        "This function should only be called for time series relationships."
    )

    input_parameter_id_to_relationship_ids_dd: defaultdict[AbsoluteParameterId, set[AbsoluteRelationshipId]] = (
        defaultdict(set)
    )
    relationship_id_to_output_parameter_ids_dd: defaultdict[AbsoluteRelationshipId, set[AbsoluteParameterId]] = (
        defaultdict(set)
    )

    match relationship.includes_past, relationship.includes_future:
        case True, True:
            raise ValueError("Relationships with both past and future dependencies are not supported.")
        case True, False:
            time_steps = list(range(1, n_time_steps))
        case False, True:
            time_steps = list(range(n_time_steps - 1))
        case False, False:
            time_steps = list(range(n_time_steps))

    for time_step in time_steps:
        relationship_id = AbsoluteTimeSeriesRelationshipId(
            model_name=core_model.name,
            name=relationship.name,
            time_step=time_step,
        )
        for input_parameter_ref in relationship.iter_input_parameter_refs():
            input_parameter = core_model.get_parameter(input_parameter_ref)
            if input_parameter.is_time_series:
                input_parameter_id: AbsoluteParameterId = AbsoluteTimeSeriesParameterId(
                    model_name=core_model.name,
                    name=input_parameter.name,
                    time_step=time_step - 1 if input_parameter_ref.previous else time_step,
                )
            else:
                input_parameter_id = AbsoluteStaticParameterId(model_name=core_model.name, name=input_parameter.name)
            input_parameter_id_to_relationship_ids_dd[input_parameter_id].add(relationship_id)

        for output_parameter_ref in relationship.iter_output_parameter_refs():
            output_parameter = core_model.get_parameter(output_parameter_ref)
            if output_parameter.is_time_series:
                output_parameter_id: AbsoluteParameterId = AbsoluteTimeSeriesParameterId(
                    model_name=core_model.name,
                    name=output_parameter.name,
                    time_step=time_step + 1 if output_parameter_ref.next else time_step,
                )
            else:
                output_parameter_id = AbsoluteStaticParameterId(model_name=core_model.name, name=output_parameter.name)
            relationship_id_to_output_parameter_ids_dd[relationship_id].add(output_parameter_id)

    return dict(input_parameter_id_to_relationship_ids_dd), dict(relationship_id_to_output_parameter_ids_dd)


def _calculate_dependencies_of_static_function_relationship(
    relationship: FunctionRelationship[Any, Any],
    *,
    core_model: CoreModel,
    n_time_steps: int,
) -> tuple[
    dict[AbsoluteParameterId, set[AbsoluteRelationshipId]],  # input_parameter_id_to_relationship_ids
    dict[AbsoluteRelationshipId, set[AbsoluteParameterId]],  # relationship_id_to_output_parameter_ids
]:
    assert not relationship.evaluated_at_each_time_step, "This function should only be called for static relationships."
    relationship_id = AbsoluteStaticRelationshipId(model_name=core_model.name, name=relationship.name)
    input_parameter_ids: set[AbsoluteParameterId] = set()
    output_parameter_ids: set[AbsoluteParameterId] = set()

    for input_parameter_ref in relationship.iter_input_parameter_refs():
        input_parameter = core_model.get_parameter(input_parameter_ref)
        if input_parameter.is_time_series:
            assert input_parameter_ref.all_time_steps, (
                "Time-series parameters for static relationships must be all-time-steps."
            )
            input_parameter_ids.update(
                AbsoluteTimeSeriesParameterId(
                    model_name=core_model.name,
                    name=input_parameter.name,
                    time_step=time_step,
                )
                for time_step in range(n_time_steps)
            )
        else:
            input_parameter_ids.add(AbsoluteStaticParameterId(model_name=core_model.name, name=input_parameter.name))

    for output_parameter_ref in relationship.iter_output_parameter_refs():
        output_parameter = core_model.get_parameter(output_parameter_ref)
        if output_parameter.is_time_series:
            match output_parameter_ref.all_time_steps, output_parameter_ref.initial:
                case True, True:
                    raise ValueError("Time-series parameters cannot be both all-time-steps and initial.")
                case True, False:
                    time_steps = list(range(n_time_steps))
                case False, True:
                    time_steps = [0]
                case False, False:
                    raise ValueError("Time-series parameters must be either all-time-steps or initial.")
            output_parameter_ids.update(
                AbsoluteTimeSeriesParameterId(
                    model_name=core_model.name,
                    name=output_parameter.name,
                    time_step=time_step,
                )
                for time_step in time_steps
            )
        else:
            output_parameter_ids.add(AbsoluteStaticParameterId(model_name=core_model.name, name=output_parameter.name))

    input_parameter_id_to_relationship_ids: dict[AbsoluteParameterId, set[AbsoluteRelationshipId]] = {
        input_parameter_id: {relationship_id} for input_parameter_id in input_parameter_ids
    }
    relationship_id_to_output_parameter_ids: dict[AbsoluteRelationshipId, set[AbsoluteParameterId]] = {
        relationship_id: output_parameter_ids
    }
    return input_parameter_id_to_relationship_ids, relationship_id_to_output_parameter_ids


def _calculate_port_mapping_of_time_series_submodel_relationship(
    relationship: SubModelRelationship,
    *,
    core_model: CoreModel,
    n_time_steps: int,
) -> dict[AbsoluteParameterId, AbsoluteParameterId]:
    sub_model = relationship._submodel
    assert sub_model is not None, "SubModelRelationship must be hydrated."
    # parent model input to sub-model input / sub-model output to parent model input
    port_mapping: dict[AbsoluteParameterId, AbsoluteParameterId] = {}

    match relationship.includes_past, relationship.includes_future:
        case True, True:
            raise ValueError("Relationships with both past and future dependencies are not supported.")
        case True, False:
            time_steps = list(range(1, n_time_steps))
        case False, True:
            time_steps = list(range(n_time_steps - 1))
        case False, False:
            time_steps = list(range(n_time_steps))

    for time_step in time_steps:
        for input_parameter_ref_inner, input_parameter_ref_outer in relationship.inputs.items():
            input_parameter_inner = sub_model.get_parameter(input_parameter_ref_inner)
            input_parameter_outer = core_model.get_parameter(input_parameter_ref_outer)
            if input_parameter_inner.is_time_series:
                input_parameter_id_inner: AbsoluteParameterId = AbsoluteTimeSeriesParameterId(
                    model_name=sub_model.name,
                    name=input_parameter_inner.name,
                    time_step=time_step,
                )
            else:
                input_parameter_id_inner = AbsoluteStaticParameterId(
                    model_name=sub_model.name,
                    name=input_parameter_inner.name,
                )

            if input_parameter_outer.is_time_series:
                input_parameter_id_outer: AbsoluteParameterId = AbsoluteTimeSeriesParameterId(
                    model_name=core_model.name,
                    name=input_parameter_outer.name,
                    time_step=time_step - 1 if input_parameter_ref_outer.previous else time_step,
                )
            else:
                input_parameter_id_outer = AbsoluteStaticParameterId(
                    model_name=core_model.name,
                    name=input_parameter_outer.name,
                )

            port_mapping[input_parameter_id_outer] = input_parameter_id_inner

        for output_parameter_ref_inner, output_parameter_ref_outer in relationship.outputs.items():
            output_parameter_inner = sub_model.get_parameter(output_parameter_ref_inner)
            output_parameter_outer = core_model.get_parameter(output_parameter_ref_outer)
            if output_parameter_inner.is_time_series:
                output_parameter_id_inner: AbsoluteParameterId = AbsoluteTimeSeriesParameterId(
                    model_name=sub_model.name,
                    name=output_parameter_inner.name,
                    time_step=time_step,
                )
            else:
                output_parameter_id_inner = AbsoluteStaticParameterId(
                    model_name=sub_model.name,
                    name=output_parameter_inner.name,
                )

            if output_parameter_outer.is_time_series:
                output_parameter_id_outer: AbsoluteParameterId = AbsoluteTimeSeriesParameterId(
                    model_name=core_model.name,
                    name=output_parameter_outer.name,
                    time_step=time_step + 1 if output_parameter_ref_outer.next else time_step,
                )
            else:
                output_parameter_id_outer = AbsoluteStaticParameterId(
                    model_name=core_model.name,
                    name=output_parameter_outer.name,
                )

            port_mapping[output_parameter_id_inner] = output_parameter_id_outer

    return port_mapping


def _calculate_port_mapping_of_static_submodel_relationship(
    relationship: SubModelRelationship,
    *,
    core_model: CoreModel,
    n_time_steps: int,
) -> dict[AbsoluteParameterId, AbsoluteParameterId]:
    sub_model = relationship._submodel
    assert sub_model is not None, "SubModelRelationship must be hydrated."
    # parent model input to sub-model input / sub-model output to parent model input
    port_mapping: dict[AbsoluteParameterId, AbsoluteParameterId] = {}

    for input_parameter_ref_inner, input_parameter_ref_outer in relationship.inputs.items():
        input_parameter_inner = sub_model.get_parameter(input_parameter_ref_inner)
        input_parameter_outer = core_model.get_parameter(input_parameter_ref_outer)
        if input_parameter_outer.is_time_series:
            assert input_parameter_ref_outer.all_time_steps, (
                "Time-series parameters for static relationships must be all-time-steps."
            )
            assert input_parameter_inner.is_time_series and input_parameter_ref_inner.all_time_steps, (
                "Parameter types must match."
            )
            port_mapping.update(
                {
                    AbsoluteTimeSeriesParameterId(
                        model_name=core_model.name,
                        name=input_parameter_outer.name,
                        time_step=time_step,
                    ): AbsoluteTimeSeriesParameterId(
                        model_name=sub_model.name,
                        name=input_parameter_inner.name,
                        time_step=time_step,
                    )
                    for time_step in range(n_time_steps)
                }
            )
        else:
            assert not input_parameter_outer.is_time_series, "Parameter types must match."
            port_mapping[AbsoluteStaticParameterId(model_name=core_model.name, name=input_parameter_outer.name)] = (
                AbsoluteStaticParameterId(model_name=sub_model.name, name=input_parameter_inner.name)
            )

    for output_parameter_ref_inner, output_parameter_ref_outer in relationship.outputs.items():
        output_parameter_inner = sub_model.get_parameter(output_parameter_ref_inner)
        output_parameter_outer = core_model.get_parameter(output_parameter_ref_outer)
        if output_parameter_outer.is_time_series:
            assert output_parameter_inner.is_time_series, "Parameter types must match."

            assert (output_parameter_ref_outer.all_time_steps and output_parameter_ref_inner.all_time_steps) or (
                output_parameter_ref_outer.initial and output_parameter_ref_inner.initial
            ), "Parameter types must match."

            if output_parameter_ref_outer.all_time_steps:
                time_steps = list(range(n_time_steps))
            else:
                time_steps = [0]

            port_mapping.update(
                {
                    AbsoluteTimeSeriesParameterId(
                        model_name=sub_model.name,
                        name=output_parameter_inner.name,
                        time_step=time_step,
                    ): AbsoluteTimeSeriesParameterId(
                        model_name=core_model.name,
                        name=output_parameter_outer.name,
                        time_step=time_step,
                    )
                    for time_step in time_steps
                }
            )
        else:
            assert not output_parameter_inner.is_time_series, "Parameter types must match."
            port_mapping[AbsoluteStaticParameterId(model_name=sub_model.name, name=output_parameter_inner.name)] = (
                AbsoluteStaticParameterId(model_name=core_model.name, name=output_parameter_outer.name)
            )

    return port_mapping


def create_exec_model_from_core_model(
    core_model: CoreModel,
    *,
    n_time_steps: int = 1,
) -> ExecutionModel:
    parameter_ids: set[AbsoluteParameterId] = set()
    for model, parameter in _iter_parameters_recursively(core_model):
        if parameter.is_time_series:
            parameter_ids.update(
                AbsoluteTimeSeriesParameterId(
                    model_name=model.name,
                    name=parameter.name,
                    time_step=time_step,
                )
                for time_step in range(n_time_steps)
            )
        else:
            parameter_ids.add(AbsoluteStaticParameterId(model_name=model.name, name=parameter.name))

    relationships: list[FunctionRelationship[Any, Any]] = []
    input_parameter_id_to_relationship_ids: dict[AbsoluteParameterId, set[AbsoluteRelationshipId]] = {}
    relationship_id_to_output_parameter_ids: dict[AbsoluteRelationshipId, set[AbsoluteParameterId]] = {}
    port_mapping: dict[AbsoluteParameterId, AbsoluteParameterId] = {}

    for model, function_relationship in _iter_function_relationships_recursively(core_model):
        relationships.append(function_relationship)
        if function_relationship.evaluated_at_each_time_step:
            input_parameter_id_to_relationship_ids_local, relationship_id_to_output_parameter_ids_local = (
                _calculate_dependencies_of_time_series_function_relationship(
                    function_relationship,
                    core_model=model,
                    n_time_steps=n_time_steps,
                )
            )
        else:
            input_parameter_id_to_relationship_ids_local, relationship_id_to_output_parameter_ids_local = (
                _calculate_dependencies_of_static_function_relationship(
                    function_relationship,
                    core_model=model,
                    n_time_steps=n_time_steps,
                )
            )
        input_parameter_id_to_relationship_ids = merge_two_set_dicts(
            input_parameter_id_to_relationship_ids, input_parameter_id_to_relationship_ids_local
        )
        relationship_id_to_output_parameter_ids = merge_two_set_dicts(
            relationship_id_to_output_parameter_ids, relationship_id_to_output_parameter_ids_local
        )

    for model, sub_model_relationship in _iter_submodel_relationships_recursively(core_model):
        if sub_model_relationship.evaluated_at_each_time_step:
            port_mapping_local = _calculate_port_mapping_of_time_series_submodel_relationship(
                sub_model_relationship, core_model=model, n_time_steps=n_time_steps
            )
        else:
            port_mapping_local = _calculate_port_mapping_of_static_submodel_relationship(
                sub_model_relationship, core_model=model, n_time_steps=n_time_steps
            )
        port_mapping.update(port_mapping_local)

    return ExecutionModel(
        parameter_ids=parameter_ids,
        relationships=relationships,
        input_parameter_id_to_relationship_ids=input_parameter_id_to_relationship_ids,
        relationship_id_to_output_parameter_ids=relationship_id_to_output_parameter_ids,
        port_mapping=port_mapping,
    )
