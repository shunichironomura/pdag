from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pdag._core import CoreModel, ParameterABC, SubModelRelationship

if TYPE_CHECKING:
    from .model import StaticParameterId, TimeSeriesParameterId


def _search_for_parameter(
    model_path: tuple[str, ...],
    parameter_name: str,
    *,
    root_model: CoreModel,
) -> ParameterABC[Any]:
    if len(model_path) > 0:
        submodel_relationship = root_model.get_relationship(model_path[0])
        assert isinstance(submodel_relationship, SubModelRelationship)
        submodel = submodel_relationship.submodel
        return _search_for_parameter(
            model_path=model_path[1:],
            parameter_name=parameter_name,
            root_model=submodel,
        )

    return root_model.get_parameter(parameter_name)


def parameter_id_to_parameter(
    parameter_id: StaticParameterId | TimeSeriesParameterId,
    *,
    root_model: CoreModel,
) -> ParameterABC[Any]:
    return _search_for_parameter(
        model_path=parameter_id.model_path,
        parameter_name=parameter_id.name,
        root_model=root_model,
    )
