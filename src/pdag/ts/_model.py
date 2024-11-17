from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pdag._base import ModelBase, ParameterBase

from ._utils import DelayedParameterTs, InitialValueParameter

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


class TimeSeriesModel(ModelBase):
    def __init__(self) -> None:
        self._parameters: dict[str, ParameterBase[Any]] = {}

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
        raise NotImplementedError
