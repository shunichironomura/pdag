from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from pdag._core import (
    CoreModel,
    FunctionRelationship,
    ParameterABC,
    SubModelRelationship,
)
from pdag._core.reference import ExecInfo
from pdag.utils import merge_two_set_dicts

from .model import (
    ConnectorABC,
    ExecInfoType,
    ExecutionModel,
    FunctionRelationshipInfo,
    ModelPathType,
    ParameterId,
    RelationshipId,
    StaticParameterId,
    StaticRelationshipId,
    TimeSeriesParameterId,
    TimeSeriesRelationshipId,
)
from .ref_resolver import resolve_ref


def _iter_submodels_recursively(
    core_model: CoreModel,
    *,
    include_self: bool = False,
    _current_path: ModelPathType = (),
) -> Iterable[tuple[ModelPathType, CoreModel]]:
    assert core_model.is_hydrated(), "CoreModel must be hydrated."
    if include_self:
        yield _current_path, core_model
    for relationship in core_model.iter_all_relationships():
        if isinstance(relationship, SubModelRelationship):
            assert isinstance(relationship.name, str)
            yield from _iter_submodels_recursively(
                relationship.submodel,
                include_self=True,
                _current_path=(*_current_path, relationship.name),
            )


def _iter_function_relationships_recursively(
    core_model: CoreModel,
) -> Iterable[tuple[ModelPathType, CoreModel, FunctionRelationship[Any, Any]]]:
    """Iterate over all function relationships in the core model, including submodels.

    Yields tuples of the form (submodel_path, submodel, relationship).
    """
    assert core_model.is_hydrated(), "CoreModel must be hydrated."
    for submodel_path, submodel in _iter_submodels_recursively(
        core_model,
        include_self=True,
    ):
        for relationship in submodel.iter_all_relationships():
            if isinstance(relationship, FunctionRelationship):
                yield submodel_path, submodel, relationship


def _iter_submodel_relationships_recursively(
    core_model: CoreModel,
) -> Iterable[tuple[ModelPathType, CoreModel, SubModelRelationship]]:
    """Iterate over all submodel relationships in the core model, including submodels.

    Yields tuples of the form (submodel, relationship).
    """
    assert core_model.is_hydrated(), "CoreModel must be hydrated."
    for submodel_path, submodel in _iter_submodels_recursively(
        core_model,
        include_self=True,
    ):
        for relationship in submodel.iter_all_relationships():
            if isinstance(relationship, SubModelRelationship):
                yield submodel_path, submodel, relationship


def _iter_parameters_recursively(
    core_model: CoreModel,
) -> Iterable[tuple[ModelPathType, CoreModel, ParameterABC[Any]]]:
    """Iterate over all parameters in the core model, including submodels.

    Yields tuples of the form (submodel, parameter).
    """
    assert core_model.is_hydrated(), "CoreModel must be hydrated."
    for submodel_path, submodel in _iter_submodels_recursively(
        core_model,
        include_self=True,
    ):
        for parameter in submodel.iter_all_parameters():
            yield submodel_path, submodel, parameter


def _calculate_dependencies_of_time_series_function_relationship(
    relationship: FunctionRelationship[Any, Any],
    *,
    core_model: CoreModel,
    model_path: ModelPathType,
    n_time_steps: int,
) -> tuple[
    dict[ParameterId, set[RelationshipId]],  # input_parameter_id_to_relationship_ids
    dict[RelationshipId, set[ParameterId]],  # relationship_id_to_output_parameter_ids
    dict[
        RelationshipId,
        FunctionRelationshipInfo,
    ],  # relationship_id_to_function_relationship_info
]:
    assert relationship.at_each_time_step, "This function should only be called for time series relationships."
    assert isinstance(relationship.name, str)

    input_parameter_id_to_relationship_ids_dd: defaultdict[
        ParameterId,
        set[RelationshipId],
    ] = defaultdict(set)
    relationship_id_to_output_parameter_ids_dd: defaultdict[
        RelationshipId,
        set[ParameterId],
    ] = defaultdict(set)
    relationship_id_to_function_relationship_info: dict[
        RelationshipId,
        FunctionRelationshipInfo,
    ] = {}

    match relationship.includes_past, relationship.includes_future:
        case True, True:
            msg = "Relationships with both past and future dependencies are not supported."
            raise ValueError(msg)
        case True, False:
            time_steps = list(range(1, n_time_steps))
        case False, True:
            time_steps = list(range(n_time_steps - 1))
        case False, False:
            time_steps = list(range(n_time_steps))

    for time_step in time_steps:
        relationship_id = TimeSeriesRelationshipId(
            model_path=model_path,
            name=relationship.name,
            time_step=time_step,
        )
        input_args: dict[str, ConnectorABC | ExecInfoType] = {}
        for input_arg_name, input_parameter_ref in relationship.inputs.items():
            if isinstance(input_parameter_ref, ExecInfo):
                exec_info_type = ExecInfoType.from_exec_info(input_parameter_ref)
                input_args[input_arg_name] = exec_info_type
            else:
                input_connector = resolve_ref(
                    input_parameter_ref,
                    core_model=core_model,
                    model_path=model_path,
                    time_series_relationship=True,
                    time_step=time_step,
                )
                for input_parameter_id in input_connector.iter_parameter_ids():
                    input_parameter_id_to_relationship_ids_dd[input_parameter_id].add(
                        relationship_id,
                    )
                input_args[input_arg_name] = input_connector

        output_args: list[ConnectorABC] = []
        for output_parameter_ref in relationship.outputs:
            output_info = resolve_ref(
                output_parameter_ref,
                core_model=core_model,
                model_path=model_path,
                time_series_relationship=True,
                time_step=time_step,
            )
            relationship_id_to_output_parameter_ids_dd[relationship_id].update(
                output_info.iter_parameter_ids(),
            )
            output_args.append(output_info)

        relationship_id_to_function_relationship_info[relationship_id] = FunctionRelationshipInfo(
            function_relationship=relationship,
            input_parameter_info=input_args,
            output_parameter_info=tuple(output_args),
        )

    return (
        dict(input_parameter_id_to_relationship_ids_dd),
        dict(relationship_id_to_output_parameter_ids_dd),
        relationship_id_to_function_relationship_info,
    )


def _calculate_dependencies_of_static_function_relationship(
    relationship: FunctionRelationship[Any, Any],
    *,
    core_model: CoreModel,
    model_path: ModelPathType,
    n_time_steps: int,
) -> tuple[
    dict[ParameterId, set[RelationshipId]],  # input_parameter_id_to_relationship_ids
    dict[RelationshipId, set[ParameterId]],  # relationship_id_to_output_parameter_ids
    dict[
        RelationshipId,
        FunctionRelationshipInfo,
    ],  # relationship_id_to_function_relationship_info
]:
    assert not relationship.at_each_time_step, "This function should only be called for static relationships."
    assert isinstance(relationship.name, str)

    relationship_id = StaticRelationshipId(
        model_path=model_path,
        name=relationship.name,
    )
    input_parameter_ids: set[ParameterId] = set()
    output_parameter_ids: set[ParameterId] = set()

    input_args: dict[str, ConnectorABC | ExecInfoType] = {}
    for input_arg_name, input_parameter_ref in relationship.inputs.items():
        if isinstance(input_parameter_ref, ExecInfo):
            exec_info_type = ExecInfoType.from_exec_info(input_parameter_ref)
            input_args[input_arg_name] = exec_info_type
        else:
            input_info = resolve_ref(
                input_parameter_ref,
                core_model=core_model,
                model_path=model_path,
                time_series_relationship=False,
                n_time_steps=n_time_steps,
            )
            input_args[input_arg_name] = input_info
            input_parameter_ids.update(input_info.iter_parameter_ids())

    output_args: list[ConnectorABC] = []
    for output_parameter_ref in relationship.outputs:
        output_info = resolve_ref(
            output_parameter_ref,
            core_model=core_model,
            model_path=model_path,
            time_series_relationship=False,
            n_time_steps=n_time_steps,
        )
        output_parameter_ids.update(output_info.iter_parameter_ids())
        output_args.append(output_info)

    input_parameter_id_to_relationship_ids: dict[ParameterId, set[RelationshipId]] = {
        input_parameter_id: {relationship_id} for input_parameter_id in input_parameter_ids
    }
    relationship_id_to_output_parameter_ids: dict[RelationshipId, set[ParameterId]] = {
        relationship_id: output_parameter_ids,
    }
    relationship_id_to_function_relationship_info: dict[
        RelationshipId,
        FunctionRelationshipInfo,
    ] = {
        relationship_id: FunctionRelationshipInfo(
            function_relationship=relationship,
            input_parameter_info=input_args,
            output_parameter_info=tuple(output_args),
        ),
    }
    return (
        input_parameter_id_to_relationship_ids,
        relationship_id_to_output_parameter_ids,
        relationship_id_to_function_relationship_info,
    )


def _calculate_port_mapping_of_time_series_submodel_relationship(
    relationship: SubModelRelationship,
    *,
    core_model: CoreModel,
    model_path: ModelPathType,
    n_time_steps: int,
) -> dict[ParameterId, ParameterId]:
    # parent model input to sub-model input / sub-model output to parent model input
    port_mapping: dict[ParameterId, ParameterId] = {}

    assert isinstance(relationship.name, str)
    submodel_path = (*model_path, relationship.name)

    match relationship.includes_past, relationship.includes_future:
        case True, True:
            msg = "Relationships with both past and future dependencies are not supported."
            raise ValueError(msg)
        case True, False:
            time_steps = list(range(1, n_time_steps))
        case False, True:
            time_steps = list(range(n_time_steps - 1))
        case False, False:
            time_steps = list(range(n_time_steps))

    for time_step in time_steps:
        for (
            input_parameter_ref_inner,
            input_parameter_ref_outer,
        ) in relationship.inputs.items():
            input_parameter_inner = resolve_ref(
                input_parameter_ref_inner,
                core_model=relationship.submodel,
                model_path=submodel_path,
                time_series_relationship=True,
                time_step=time_step,
            )
            input_parameter_outer = resolve_ref(
                input_parameter_ref_outer,
                core_model=core_model,
                model_path=model_path,
                time_series_relationship=True,
                time_step=time_step,
            )
            for input_parameter_id_inner, input_parameter_id_outer in zip(
                input_parameter_inner.iter_parameter_ids(),
                input_parameter_outer.iter_parameter_ids(),
                strict=True,
            ):
                port_mapping[input_parameter_id_outer] = input_parameter_id_inner  # noqa: PERF403

        for (
            output_parameter_ref_inner,
            output_parameter_ref_outer,
        ) in relationship.outputs.items():
            output_parameter_inner = resolve_ref(
                output_parameter_ref_inner,
                core_model=relationship.submodel,
                model_path=submodel_path,
                time_series_relationship=True,
                time_step=time_step,
            )
            output_parameter_outer = resolve_ref(
                output_parameter_ref_outer,
                core_model=core_model,
                model_path=model_path,
                time_series_relationship=True,
                time_step=time_step,
            )
            for output_parameter_id_inner, output_parameter_id_outer in zip(
                output_parameter_inner.iter_parameter_ids(),
                output_parameter_outer.iter_parameter_ids(),
                strict=True,
            ):
                port_mapping[output_parameter_id_inner] = output_parameter_id_outer  # noqa: PERF403

    return port_mapping


def _calculate_port_mapping_of_static_submodel_relationship(
    relationship: SubModelRelationship,
    *,
    core_model: CoreModel,
    model_path: ModelPathType,
    n_time_steps: int,
) -> dict[ParameterId, ParameterId]:
    # parent model input to sub-model input / sub-model output to parent model input
    port_mapping: dict[ParameterId, ParameterId] = {}

    assert isinstance(relationship.name, str)
    submodel_path = (*model_path, relationship.name)

    for (
        input_parameter_ref_inner,
        input_parameter_ref_outer,
    ) in relationship.inputs.items():
        input_parameter_inner = resolve_ref(
            input_parameter_ref_inner,
            core_model=relationship.submodel,
            model_path=submodel_path,
            time_series_relationship=False,
            n_time_steps=n_time_steps,
        )
        input_parameter_outer = resolve_ref(
            input_parameter_ref_outer,
            core_model=core_model,
            model_path=model_path,
            time_series_relationship=False,
            n_time_steps=n_time_steps,
        )
        for input_parameter_id_inner, input_parmaeter_id_outer in zip(
            input_parameter_inner.iter_parameter_ids(),
            input_parameter_outer.iter_parameter_ids(),
            strict=True,
        ):
            port_mapping[input_parmaeter_id_outer] = input_parameter_id_inner  # noqa: PERF403

    for (
        output_parameter_ref_inner,
        output_parameter_ref_outer,
    ) in relationship.outputs.items():
        output_parameter_inner = resolve_ref(
            output_parameter_ref_inner,
            core_model=relationship.submodel,
            model_path=submodel_path,
            time_series_relationship=False,
            n_time_steps=n_time_steps,
        )
        output_parameter_outer = resolve_ref(
            output_parameter_ref_outer,
            core_model=core_model,
            model_path=model_path,
            time_series_relationship=False,
            n_time_steps=n_time_steps,
        )
        for output_parameter_id_inner, output_parameter_id_outer in zip(
            output_parameter_inner.iter_parameter_ids(),
            output_parameter_outer.iter_parameter_ids(),
            strict=True,
        ):
            port_mapping[output_parameter_id_inner] = output_parameter_id_outer  # noqa: PERF403

    return port_mapping


def create_exec_model_from_core_model(
    core_model: CoreModel,
    *,
    n_time_steps: int = 1,
) -> ExecutionModel:
    parameter_ids: set[ParameterId] = set()
    for model_path, _, parameter in _iter_parameters_recursively(core_model):
        assert isinstance(parameter.name, str)
        if parameter.is_time_series:
            parameter_ids.update(
                TimeSeriesParameterId(
                    model_path=model_path,
                    name=parameter.name,
                    time_step=time_step,
                )
                for time_step in range(n_time_steps)
            )
        else:
            parameter_ids.add(
                StaticParameterId(model_path=model_path, name=parameter.name),
            )

    relationships: dict[RelationshipId, FunctionRelationshipInfo] = {}
    input_parameter_id_to_relationship_ids: dict[ParameterId, set[RelationshipId]] = {}
    relationship_id_to_output_parameter_ids: dict[RelationshipId, set[ParameterId]] = {}
    port_mapping: dict[ParameterId, ParameterId] = {}

    for (
        model_path,
        model,
        function_relationship,
    ) in _iter_function_relationships_recursively(core_model):
        if function_relationship.at_each_time_step:
            (
                input_parameter_id_to_relationship_ids_local,
                relationship_id_to_output_parameter_ids_local,
                relationships_local,
            ) = _calculate_dependencies_of_time_series_function_relationship(
                function_relationship,
                core_model=model,
                model_path=model_path,
                n_time_steps=n_time_steps,
            )
        else:
            (
                input_parameter_id_to_relationship_ids_local,
                relationship_id_to_output_parameter_ids_local,
                relationships_local,
            ) = _calculate_dependencies_of_static_function_relationship(
                function_relationship,
                core_model=model,
                model_path=model_path,
                n_time_steps=n_time_steps,
            )
        relationships.update(relationships_local)

        input_parameter_id_to_relationship_ids = merge_two_set_dicts(
            input_parameter_id_to_relationship_ids,
            input_parameter_id_to_relationship_ids_local,
        )
        relationship_id_to_output_parameter_ids = merge_two_set_dicts(
            relationship_id_to_output_parameter_ids,
            relationship_id_to_output_parameter_ids_local,
        )

    for (
        model_path,
        model,
        sub_model_relationship,
    ) in _iter_submodel_relationships_recursively(core_model):
        if sub_model_relationship.at_each_time_step:
            port_mapping_local = _calculate_port_mapping_of_time_series_submodel_relationship(
                sub_model_relationship,
                core_model=model,
                model_path=model_path,
                n_time_steps=n_time_steps,
            )
        else:
            port_mapping_local = _calculate_port_mapping_of_static_submodel_relationship(
                sub_model_relationship,
                core_model=model,
                model_path=model_path,
                n_time_steps=n_time_steps,
            )
        port_mapping.update(port_mapping_local)

    return ExecutionModel(
        parameter_ids=parameter_ids,
        relationship_infos=relationships,
        input_parameter_id_to_relationship_ids=input_parameter_id_to_relationship_ids,
        relationship_id_to_output_parameter_ids=relationship_id_to_output_parameter_ids,
        port_mapping=port_mapping,
        n_time_steps=n_time_steps,
        _core_model=core_model,
    )
