import inspect
from collections.abc import Callable, Hashable
from types import EllipsisType
from typing import Any, get_args, get_origin, overload

from typing_extensions import _AnnotatedAlias

from pdag._core import (
    ExecInfo,
    FunctionRelationship,
    ReferenceABC,
)
from pdag.utils import MultiDefProtocol, get_function_body, multidef


def _get_outputs_from_signature(
    sig: inspect.Signature,
) -> tuple[list[ReferenceABC], bool]:
    def single_annotation_to_ref(
        annotations: _AnnotatedAlias,
    ) -> ReferenceABC:
        args = get_args(annotations)
        return next(iter(arg for arg in args if isinstance(arg, ReferenceABC)))

    if get_origin(sig.return_annotation) is not tuple:
        parameter_name = single_annotation_to_ref(sig.return_annotation)
        return [parameter_name], True
    args = get_args(sig.return_annotation)
    return [single_annotation_to_ref(arg) for arg in args], False


def _get_inputs_from_signature(
    sig: inspect.Signature,
) -> dict[str, ReferenceABC | ExecInfo]:
    def _get_ref_from_annotation(
        annotations: _AnnotatedAlias,
    ) -> ReferenceABC | ExecInfo | None:
        args = get_args(annotations)
        try:
            return next(iter(arg for arg in args if isinstance(arg, ReferenceABC | ExecInfo)))
        except StopIteration:
            return None

    return {
        param.name: ref
        for param in sig.parameters.values()
        if (ref := _get_ref_from_annotation(param.annotation)) is not None
    }


@overload
def relationship[**P, T](
    func: Callable[P, T],
    *,
    identifier: None = None,
) -> FunctionRelationship[P, T]: ...


@overload
def relationship[**P, T](
    func: None = None,
    *,
    identifier: Any = None,
) -> Callable[[Callable[P, T]], FunctionRelationship[P, T]]: ...


def relationship[**P, T](
    func: Callable[P, T] | None = None,
    *,
    identifier: Hashable = None,
) -> (
    FunctionRelationship[P, T]
    | Callable[[Callable[P, T]], FunctionRelationship[P, T]]
    | Callable[[Callable[P, T]], MultiDefProtocol[Hashable, FunctionRelationship[P, T]]]
):
    """Decorate a function to mark it as a relationship."""

    def decorator(
        func: Callable[P, T],
        *,
        _relationship_name: str | EllipsisType | None = None,
    ) -> FunctionRelationship[P, T]:
        # Get the function's signature
        sig = inspect.signature(func)
        inputs = _get_inputs_from_signature(sig)
        outputs, output_is_scalar = _get_outputs_from_signature(sig)
        function_body = get_function_body(func)
        return FunctionRelationship(
            name=func.__name__ if _relationship_name is None else _relationship_name,
            inputs=inputs,
            outputs=outputs,
            function_body=function_body,
            output_is_scalar=output_is_scalar,
            _function=func,
        )

    if func is not None:
        # If the decorator is used without parentheses, we need to return the decorator
        return decorator(func)

    if identifier is None:
        return decorator

    # If the identifier is provided, we need to return decorator to return multidef

    def decorator_for_multidef(
        func: Callable[P, T],
    ) -> MultiDefProtocol[Hashable, FunctionRelationship[P, T]]:
        return multidef(identifier)(decorator(func, _relationship_name=...))

    return decorator_for_multidef
