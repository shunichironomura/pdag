import inspect
from collections.abc import Callable, Hashable
from types import EllipsisType
from typing import Any, Literal, get_args, get_origin, overload

from typing_extensions import _AnnotatedAlias

from pdag._core import (
    ExecInfo,
    ReferenceABC,
)
from pdag._core.builder import FunctionRelationshipBuilder, ReferenceBuilder
from pdag.utils import MultiDefProtocol, get_function_body, multidef


def _get_outputs_from_signature(
    sig: inspect.Signature,
) -> tuple[list[ReferenceABC | ReferenceBuilder[Any]], bool]:
    def single_annotation_to_ref(
        annotations: _AnnotatedAlias,
    ) -> ReferenceABC | ReferenceBuilder[Any]:
        args = get_args(annotations)
        return next(iter(arg for arg in args if isinstance(arg, ReferenceABC | ReferenceBuilder)))

    if get_origin(sig.return_annotation) is not tuple:
        parameter_name = single_annotation_to_ref(sig.return_annotation)
        return [parameter_name], True
    args = get_args(sig.return_annotation)
    return [single_annotation_to_ref(arg) for arg in args], False


def _get_inputs_from_signature(
    sig: inspect.Signature,
) -> dict[str, ReferenceABC | ReferenceBuilder[Any] | ExecInfo]:
    """Get the input references from the signature of a function.

    The references are extracted from the annotations of the function's parameters.
    Note that it is possible that an argument does not have a reference annotation.
    For example, users may bind the loop variable in a for loop as the default value of a function argument.
    In this case, we return None, and the argument will be ignored.

    Example:
    ```python
    class MyModel(pdag.Model):
        for k in ["a", "b"]:
            @pdag.relationship(identifier=k)
            @staticmethod
            def f(
                x: Annotated[floag, pdag.ParameterRef("x")],
                k: str = k, # k is bound to the loop variable
            ) -> Annotated[float, pdag.ParameterRef("y")]:
                pass
    ```

    """

    def _get_ref_from_annotation(
        annotations: _AnnotatedAlias,
    ) -> ReferenceABC | ReferenceBuilder[Any] | ExecInfo | None:
        args = get_args(annotations)
        try:
            return next(iter(arg for arg in args if isinstance(arg, ReferenceABC | ReferenceBuilder | ExecInfo)))
        except StopIteration:
            # No annotation of type ReferenceABC or ExecInfo found.
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
    at_each_time_step: Literal[False] = False,
) -> FunctionRelationshipBuilder[P, T]: ...


@overload
def relationship[**P, T](
    func: None = None,
    *,
    identifier: Any = None,
    at_each_time_step: bool = False,
) -> Callable[[Callable[P, T]], FunctionRelationshipBuilder[P, T]]: ...


def relationship[**P, T](
    func: Callable[P, T] | None = None,
    *,
    identifier: Hashable = None,
    at_each_time_step: bool = False,
) -> (
    FunctionRelationshipBuilder[P, T]
    | Callable[[Callable[P, T]], FunctionRelationshipBuilder[P, T]]
    | Callable[[Callable[P, T]], MultiDefProtocol[Hashable, FunctionRelationshipBuilder[P, T]]]
):
    """Decorate a function to mark it as a relationship."""

    def decorator(
        func: Callable[P, T],
        *,
        _relationship_name: str | EllipsisType | None = None,
    ) -> FunctionRelationshipBuilder[P, T]:
        # Get the function's signature
        sig = inspect.signature(func)
        inputs = _get_inputs_from_signature(sig)
        outputs, output_is_scalar = _get_outputs_from_signature(sig)
        function_body = get_function_body(func)
        return FunctionRelationshipBuilder(
            name=func.__name__ if _relationship_name is None else _relationship_name,
            inputs=inputs,
            outputs=outputs,
            function_body=function_body,
            output_is_scalar=output_is_scalar,
            _function=func,
            at_each_time_step=at_each_time_step,
        )

    if func is not None:
        # If the decorator is used without parentheses, we need to return the decorator
        return decorator(func)

    if identifier is None:
        return decorator

    # If the identifier is provided, we need to return decorator to return multidef

    def decorator_for_multidef(
        func: Callable[P, T],
    ) -> MultiDefProtocol[Hashable, FunctionRelationshipBuilder[P, T]]:
        return multidef(identifier)(decorator(func, _relationship_name=...))

    return decorator_for_multidef
