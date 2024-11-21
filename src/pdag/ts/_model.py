from __future__ import annotations

import logging
from dataclasses import dataclass, field
from functools import wraps
from typing import TYPE_CHECKING, Any

from pdag._base import ModelBase, ParameterBase
from pdag.ts._parameter import ParameterTsBase

from ._utils import DelayedParameterTs, InitialValueParameter

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Relationship:
    name: str
    function: Callable[..., tuple[Any, ...]] = field(repr=False)
    inputs: tuple[ParameterBase[Any], ...]
    outputs: tuple[ParameterBase[Any], ...]

    def evaluate(self, *args: Any, time_index: int | None = None) -> tuple[Any, ...]:
        if self.is_snapshot_relationship():
            return self.function(*args)
        return self.function(*args)

    def is_snapshot_relationship(self) -> bool:
        return all(isinstance(output, ParameterTsBase) for output in self.outputs)


class TimeSeriesModel(ModelBase):
    def __init__(self) -> None:
        self._parameters: dict[str, ParameterBase[Any]] = {}
        self._relationships: dict[str, Relationship] = {}
        self._predecessor_relationships: dict[str, set[str]] = {}
        self._successor_relationships: dict[str, set[str]] = {}

    def add_parameter(self, parameter: ParameterBase[Any]) -> None:
        if parameter.name in self._parameters and not isinstance(parameter, InitialValueParameter | DelayedParameterTs):
            msg = f"Parameter {parameter} is already in the model."
            raise ValueError(msg)
        self._parameters[parameter.name] = parameter

    def add_relationship(
        self,
        function: Callable[..., Any],
        inputs: tuple[ParameterBase[Any], ...] | ParameterBase[Any],
        outputs: tuple[ParameterBase[Any], ...] | ParameterBase[Any],
    ) -> None:
        if isinstance(inputs, ParameterBase):
            inputs = (inputs,)
        if isinstance(outputs, ParameterBase):
            outputs = (outputs,)

            @wraps(function)
            def _function(*args: Any) -> tuple[Any, ...]:
                return (function(*args),)
        else:
            _function = wraps(function)(function)

        relationship = Relationship(name=function.__name__, function=_function, inputs=inputs, outputs=outputs)
        self._relationships[function.__name__] = relationship
        for input_ in inputs:
            self._predecessor_relationships.setdefault(input_.name, set()).add(function.__name__)
        for output in outputs:
            self._successor_relationships.setdefault(output.name, set()).add(function.__name__)

    def iter_parameters(self) -> Generator[ParameterBase[Any]]:
        yield from self._parameters.values()


class TimeSeriesModelEvaluator:
    def __init__(self, model: TimeSeriesModel) -> None:
        self._model = model

    def evaluate(self, inputs: dict[ParameterBase[Any], Any]) -> dict[ParameterBase[Any], Any]:
        results = {}
        memoized_evaluations = inputs.copy()

        for parameter in self._model.iter_parameters():
            logger.debug(f"Evaluating {parameter}")
            memoized_evaluations = self._update_memoized_evaluations(
                parameter=parameter,
                memoized_evaluations=memoized_evaluations,
            )
            results[parameter] = memoized_evaluations[parameter]

        return results

    def _update_memoized_evaluations(
        self,
        parameter: ParameterBase[Any],
        memoized_evaluations: dict[ParameterBase[Any], Any],
    ) -> dict[ParameterBase[Any], Any]:
        if parameter in memoized_evaluations:
            return memoized_evaluations

        for relationship_name in self._model._predecessor_relationships.get(parameter.name, []):
            relationship = self._model._relationships[relationship_name]
            args = tuple(memoized_evaluations[input_] for input_ in relationship.inputs)
            memoized_evaluations[parameter] = relationship.function(*args)

        return memoized_evaluations
