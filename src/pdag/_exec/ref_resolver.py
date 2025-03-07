from collections.abc import Hashable
from collections.abc import Mapping as MappingABC
from types import EllipsisType
from typing import Any

import numpy as np
import numpy.typing as npt

from pdag._core import ReferenceABC
from pdag._core.collection import Array, CollectionABC, Mapping
from pdag._core.model import CoreModel
from pdag._core.parameter import ParameterABC
from pdag._core.reference import CollectionRef, ParameterRef

from .model import (
    ArrayConnector,
    ConnectorABC,
    MappingConnector,
    MappingListConnector,
    ModelPathType,
    ParameterId,
    ScalarConnector,
    StaticParameterId,
    TimeSeriesParameterId,
)


def _mapping_to_array[T](
    mapping: MappingABC[tuple[int, ...], T],
    shape: tuple[int, ...],
    *,
    error_on_missing: bool = False,
) -> npt.NDArray[T]:  # type: ignore[type-var]
    array = np.empty(shape, dtype=object)
    for key, value in mapping.items():
        array[key] = value
    if error_on_missing and np.any(array == None):  # noqa: E711
        msg = "Missing values in mapping."
        raise ValueError(msg)
    return array


def resolve_ref(  # noqa: PLR0913
    ref: ReferenceABC,
    *,
    core_model: CoreModel,
    model_path: ModelPathType,
    time_series_relationship: bool,
    n_time_steps: int | None = None,
    time_step: int | None = None,
) -> ConnectorABC:
    obj = core_model.get_object_from_ref(ref)
    if isinstance(obj, ParameterABC):
        assert isinstance(ref, ParameterRef)
        if time_series_relationship:
            assert time_step is not None
            return _resolve_parameter_ref_in_time_series_relationship(
                ref=ref,
                model_path=model_path,
                parameter=obj,
                time_step=time_step,
            )
        assert n_time_steps is not None
        return _resolve_parameter_ref_in_static_relationship(
            ref=ref,
            model_path=model_path,
            parameter=obj,
            n_time_steps=n_time_steps,
        )
    if isinstance(obj, CollectionABC):
        assert isinstance(ref, CollectionRef)
        if time_series_relationship:
            assert time_step is not None
            return _resolve_collection_ref_in_time_series_relationship(
                ref=ref,
                model_path=model_path,
                collection=obj,
                time_step=time_step,
            )
        assert n_time_steps is not None
        return _resolve_collection_ref_in_static_relationship(
            ref=ref,
            model_path=model_path,
            collection=obj,
            n_time_steps=n_time_steps,
        )

    raise NotImplementedError


def _resolve_parameter_ref_in_time_series_relationship(
    ref: ParameterRef,
    *,
    model_path: ModelPathType,
    parameter: ParameterABC[Any],
    time_step: int,
) -> ConnectorABC:
    assert isinstance(parameter.name, str)
    if ref.normal:
        param_time_step = time_step
    elif ref.previous:
        param_time_step = time_step - 1
    elif ref.next:
        param_time_step = time_step + 1
    else:
        msg = "Unsupported reference type."
        raise ValueError(msg)

    if parameter.is_time_series:
        input_parameter_id: ParameterId = TimeSeriesParameterId(
            model_path=model_path,
            name=parameter.name,
            time_step=param_time_step,
        )
    else:
        input_parameter_id = StaticParameterId(
            model_path=model_path,
            name=parameter.name,
        )

    return ScalarConnector(parameter_id=input_parameter_id)


def _resolve_collection_ref_in_time_series_relationship(
    ref: CollectionRef[Hashable],
    *,
    model_path: ModelPathType,
    collection: CollectionABC[Any, ParameterABC[Any]],
    time_step: int,
) -> ConnectorABC:
    if collection.is_time_series():
        if ref.normal:
            param_time_step = time_step
        elif ref.previous:
            param_time_step = time_step - 1
        elif ref.next:
            param_time_step = time_step + 1
        else:
            msg = "Unsupported reference type."
            raise ValueError(msg)

        parameter_ids: dict[Hashable, ParameterId] = {
            key: TimeSeriesParameterId(
                model_path=model_path,
                name=parameter.name,  # type: ignore[arg-type]
                time_step=param_time_step,
            )
            for key, parameter in collection.items()
        }
    else:
        parameter_ids = {
            key: StaticParameterId(model_path=model_path, name=parameter.name)  # type: ignore[arg-type]
            for key, parameter in collection.items()
        }

    if isinstance(collection, Mapping):
        return _filter(MappingConnector(parameter_ids=parameter_ids), key=ref.key)
    if isinstance(collection, Array):
        return ArrayConnector(
            parameter_ids=_mapping_to_array(
                parameter_ids,  # type: ignore[arg-type]
                shape=collection.shape,
                error_on_missing=True,
            ),
        )

    msg = f"Unsupported collection type: {collection}"
    raise ValueError(msg)


def _resolve_parameter_ref_in_static_relationship(
    ref: ParameterRef,
    *,
    model_path: ModelPathType,
    parameter: ParameterABC[Any],
    n_time_steps: int,
) -> ConnectorABC:
    assert isinstance(parameter.name, str)

    if parameter.is_time_series:
        if ref.all_time_steps:
            parameter_ids: list[ParameterId] = [
                TimeSeriesParameterId(
                    model_path=model_path,
                    name=parameter.name,
                    time_step=time_step,
                )
                for time_step in range(n_time_steps)
            ]
            return ArrayConnector(parameter_ids=np.array(parameter_ids))
        if ref.initial:
            return ScalarConnector(
                parameter_id=TimeSeriesParameterId(
                    model_path=model_path,
                    name=parameter.name,
                    time_step=0,
                ),
            )
        msg = "Time-series parameter reference in static relationship must be either 'all_time_steps' or 'initial'."
        raise ValueError(msg)

    return ScalarConnector(
        parameter_id=StaticParameterId(model_path=model_path, name=parameter.name),
    )


def _resolve_collection_ref_in_static_relationship(
    ref: CollectionRef[Hashable],
    *,
    model_path: ModelPathType,
    collection: CollectionABC[Hashable, ParameterABC[Any]],
    n_time_steps: int,
) -> ConnectorABC:
    if collection.is_time_series():
        if ref.all_time_steps:
            parameter_ids_mlc: list[dict[Hashable, ParameterId]] = [
                {
                    key: TimeSeriesParameterId(
                        model_path=model_path,
                        name=parameter.name,  # type: ignore[arg-type]
                        time_step=time_step,
                    )
                    for key, parameter in collection.items()
                }
                for time_step in range(n_time_steps)
            ]
            connector: ConnectorABC = MappingListConnector(
                parameter_ids=parameter_ids_mlc,
            )
        elif ref.initial:
            parameter_ids: dict[Hashable, ParameterId] = {
                key: TimeSeriesParameterId(
                    model_path=model_path,
                    name=parameter.name,  # type: ignore[arg-type]
                    time_step=0,
                )
                for key, parameter in collection.items()
            }
            connector = MappingConnector(parameter_ids=parameter_ids)
        else:
            msg = (
                "Time-series collection reference in static relationship must be either 'all_time_steps' or 'initial'."
            )
            raise ValueError(msg)
    else:
        parameter_ids = {
            key: StaticParameterId(model_path=model_path, name=parameter.name)  # type: ignore[arg-type]
            for key, parameter in collection.items()
        }
        connector = MappingConnector(parameter_ids=parameter_ids)

    if isinstance(collection, Mapping):
        return _filter(connector, key=ref.key)
    if isinstance(collection, Array):
        if isinstance(connector, MappingListConnector):
            # Time-series of an array collection
            return ArrayConnector(
                parameter_ids=np.array(
                    [
                        _mapping_to_array(
                            mapping,  # type: ignore[arg-type]
                            shape=collection.shape,  # type: ignore[attr-defined]
                            error_on_missing=True,
                        )
                        for mapping in connector.parameter_ids
                    ],
                ),
            )
        return ArrayConnector(
            parameter_ids=_mapping_to_array(
                parameter_ids,  # type: ignore[arg-type]
                shape=collection.shape,  # type: ignore[attr-defined]
                error_on_missing=True,
            ),
        )

    msg = f"Unsupported collection type: {collection}"
    raise ValueError


def _filter(connector: ConnectorABC, key: Hashable | None = None) -> ConnectorABC:
    if key is None:
        return connector
    if isinstance(connector, MappingConnector):
        if isinstance(key, str) or (isinstance(key, tuple) and all(isinstance(k, str) for k in key)):
            return ScalarConnector(parameter_id=connector.parameter_ids[key])
        if isinstance(key, tuple):
            return MappingConnector(
                parameter_ids=_filter_mapping(connector.parameter_ids, key),  # type: ignore[arg-type]
            )
        msg = f"Unsupported key type: {key}"
        raise ValueError(msg)
    if isinstance(connector, ArrayConnector):
        msg = "Filtering an array connector is not supported."
        raise NotImplementedError(msg)
    if isinstance(connector, MappingListConnector):
        sample_key = next(iter(connector.parameter_ids[0]))
        if isinstance(sample_key, str):
            return ArrayConnector(
                parameter_ids=np.array(
                    [mapping[key] for mapping in connector.parameter_ids],
                ),
            )
        if isinstance(sample_key, tuple):
            return MappingListConnector(
                parameter_ids=_filter_mapping(connector.parameter_ids, key),  # type: ignore[arg-type]
            )
        msg = f"Unsupported key type: {sample_key}"
        raise ValueError(msg)
    msg = f"Unsupported connector type: {connector}"
    raise ValueError(msg)


def _filter_mapping[T](
    mapping: MappingABC[tuple[str, ...], T],
    key: tuple[str | EllipsisType, ...],
) -> dict[str | tuple[str, ...], T]:
    mapping_filtered = {
        key_in_mapping: value
        for key_in_mapping, value in mapping.items()
        if all(
            (k_in_mapping == k_provided) or (k_provided is Ellipsis)
            for k_in_mapping, k_provided in zip(key_in_mapping, key, strict=True)
        )
    }

    # Reduce the dimension of the key if the value is provided
    def _reduce_key(key_in_mapping: tuple[str, ...]) -> str | tuple[str, ...]:
        reduced_key = tuple(k for k, k_provided in zip(key_in_mapping, key, strict=True) if k_provided is Ellipsis)
        if len(reduced_key) == 1:
            return reduced_key[0]
        return reduced_key

    return {_reduce_key(key_in_mapping): value for key_in_mapping, value in mapping_filtered.items()}
