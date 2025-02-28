import inspect
import warnings
from abc import ABCMeta
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, dataclass_transform, get_args, get_origin

from typing_extensions import _AnnotatedAlias

from pdag._core import CoreModel, FunctionRelationship, ParameterABC, ParameterCollectionABC, RelationshipABC
from pdag.utils import get_function_body


@dataclass
class Parameter:
    name: str


def _get_inputs_from_signature(sig: inspect.Signature) -> dict[str, str]:
    def _get_param_name_from_annotation(annotations: _AnnotatedAlias) -> str:
        args = get_args(annotations)
        param = next(iter(arg for arg in args if isinstance(arg, Parameter)))
        return param.name

    return {param.name: _get_param_name_from_annotation(param.annotation) for param in sig.parameters.values()}


def _get_outputs_from_signature(sig: inspect.Signature) -> tuple[list[str], bool]:
    def single_annotation_to_parameter_name(annotations: _AnnotatedAlias) -> str:
        args = get_args(annotations)
        param = next(iter(arg for arg in args if isinstance(arg, Parameter)))
        return param.name

    if get_origin(sig.return_annotation) is not tuple:
        parameter_name = single_annotation_to_parameter_name(sig.return_annotation)
        return [parameter_name], True
    args = get_args(sig.return_annotation)
    return [single_annotation_to_parameter_name(arg) for arg in args], False


def _staticmethod_to_function_relationship(func: Callable[..., Any]) -> FunctionRelationship:
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


@dataclass_transform()
class ModelMeta(ABCMeta):
    def __new__(metacls, name: str, bases: tuple[type[Any], ...], namespace: dict[str, Any]) -> type:  # noqa: N804
        cls = super().__new__(metacls, name, bases, namespace)
        cls.__pdag_parameters__ = {}  # type: ignore[attr-defined]
        cls.__pdag_collections__ = {}  # type: ignore[attr-defined]
        cls.__pdag_relationships__ = {}  # type: ignore[attr-defined]

        annotations = inspect.get_annotations(cls)
        for attribute_name, attribute_type in annotations.items():
            try:
                parameter = next(iter(arg for arg in get_args(attribute_type) if isinstance(arg, ParameterABC)))
            except StopIteration:
                warnings.warn(f"Attribute {attribute_name} of {cls.__name__} is not a valid parameter.", stacklevel=2)
                continue

            # TODO: Check validity of parameter definition
            cls.__pdag_parameters__[attribute_name] = parameter  # type: ignore[attr-defined]

        for attr, value in namespace.items():
            if hasattr(value, "__is_pdag_relationship__") and value.__is_pdag_relationship__:
                # TODO: Check validity of relationship definition
                cls.__pdag_relationships__[attr] = _staticmethod_to_function_relationship(value)  # type: ignore[attr-defined]

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
