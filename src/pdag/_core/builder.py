from collections.abc import Callable
from dataclasses import dataclass, field
from types import EllipsisType
from typing import Any

from .parameter import ParameterABC
from .reference import (
    ExecInfo,
    ParameterRef,
    ReferenceABC,
)
from .relationship import FunctionRelationship


@dataclass
class ReferenceBuilder[T]:
    parameter: ParameterABC[T]
    previous: bool = field(default=False, kw_only=True)
    next: bool = field(default=False, kw_only=True)
    initial: bool = field(default=False, kw_only=True)
    all_time_steps: bool = field(default=False, kw_only=True)

    def build(self) -> ParameterRef:
        return ParameterRef(
            name=self.parameter.name,
            previous=self.previous,
            next=self.next,
            initial=self.initial,
            all_time_steps=self.all_time_steps,
        )


@dataclass
class FunctionRelationshipBuilder[**P, T]:
    name: str | EllipsisType
    at_each_time_step: bool = field(default=False, kw_only=True)
    inputs: dict[str, ReferenceABC | ReferenceBuilder[Any] | ExecInfo] = field(kw_only=True)
    outputs: list[ReferenceABC | ReferenceBuilder[Any]] = field(kw_only=True)
    function_body: str = field(kw_only=True)
    output_is_scalar: bool = field(kw_only=True)
    _function: Callable[P, T] | None = field(default=None, compare=False, kw_only=True)

    def build(self) -> FunctionRelationship[P, T]:
        return FunctionRelationship(
            name=self.name,
            inputs={
                name: ref.build() if isinstance(ref, ReferenceBuilder) else ref for name, ref in self.inputs.items()
            },
            outputs=[ref.build() if isinstance(ref, ReferenceBuilder) else ref for ref in self.outputs],
            function_body=self.function_body,
            at_each_time_step=self.at_each_time_step,
            output_is_scalar=self.output_is_scalar,
            _function=self._function,
        )
