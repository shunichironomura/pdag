import inspect
from abc import ABCMeta
from collections.abc import Callable, Mapping
from typing import Any, get_args, get_origin

from typing_extensions import _AnnotatedAlias

from pdag._core import (
    CoreModel,
    FunctionRelationship,
    ParameterABC,
    ParameterCollectionABC,
    ParameterRef,
    RelationshipABC,
    SubModelRelationship,
)
from pdag.utils import get_function_body


def _get_inputs_from_signature(sig: inspect.Signature) -> dict[str, ParameterRef]:
    def _get_param_ref_from_annotation(annotations: _AnnotatedAlias) -> ParameterRef:
        args = get_args(annotations)
        return next(iter(arg for arg in args if isinstance(arg, ParameterRef)))

    return {param.name: _get_param_ref_from_annotation(param.annotation) for param in sig.parameters.values()}


def _get_outputs_from_signature(sig: inspect.Signature) -> tuple[list[ParameterRef], bool]:
    def single_annotation_to_parameter_ref(annotations: _AnnotatedAlias) -> ParameterRef:
        args = get_args(annotations)
        return next(iter(arg for arg in args if isinstance(arg, ParameterRef)))

    if get_origin(sig.return_annotation) is not tuple:
        parameter_name = single_annotation_to_parameter_ref(sig.return_annotation)
        return [parameter_name], True
    args = get_args(sig.return_annotation)
    return [single_annotation_to_parameter_ref(arg) for arg in args], False


def function_to_function_relationship[**P, T](func: Callable[P, T]) -> FunctionRelationship[P, T]:
    # Get the function's signature
    sig = inspect.signature(func)
    inputs = _get_inputs_from_signature(sig)
    outputs, output_is_scalar = _get_outputs_from_signature(sig)
    function_body = get_function_body(func)
    return FunctionRelationship(
        name=func.__name__,
        inputs=inputs,
        outputs=outputs,
        function_body=function_body,
        output_is_scalar=output_is_scalar,
        _function=func,
    )


class ModelMeta(ABCMeta):
    def __new__(metacls, name: str, bases: tuple[type[Any], ...], namespace: dict[str, Any]) -> type:  # noqa: N804
        cls = super().__new__(metacls, name, bases, namespace)
        cls.__pdag_collections__ = {}  # type: ignore[attr-defined]

        cls.__pdag_parameters__ = {name: value for name, value in namespace.items() if isinstance(value, ParameterABC)}  # type: ignore[attr-defined]

        # TODO: Check validity of relationship definition
        cls.__pdag_relationships__ = {  # type: ignore[attr-defined]
            name: value for name, value in namespace.items() if isinstance(value, RelationshipABC)
        }

        return cls


class Model(metaclass=ModelMeta):
    @classmethod
    def parameters(cls) -> dict[str, ParameterABC[Any]]:
        return cls.__pdag_parameters__  # type: ignore[attr-defined,no-any-return]

    @classmethod
    def collections(cls) -> dict[str, ParameterCollectionABC]:
        return {}  # TODO: Implement

    @classmethod
    def relationships(cls) -> dict[str, RelationshipABC]:
        return cls.__pdag_relationships__  # type: ignore[attr-defined,no-any-return]

    @classmethod
    def to_core_model(cls) -> CoreModel:
        return CoreModel(
            name=cls.__name__,
            parameters=cls.parameters(),
            collections=cls.collections(),
            relationships=cls.relationships(),
        )

    @classmethod
    def to_relationship(
        cls,
        /,
        name: str,
        *,
        inputs: Mapping[ParameterRef, ParameterRef],
        outputs: Mapping[ParameterRef, ParameterRef],
    ) -> SubModelRelationship:
        return SubModelRelationship(
            name=name,
            submodel_name=cls.__name__,
            inputs=dict(inputs),
            outputs=dict(outputs),
            _submodel=cls.to_core_model(),
        )
