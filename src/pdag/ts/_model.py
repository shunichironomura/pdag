from __future__ import annotations

import logging
from typing import Any

from pdag._base import ModelBase, ParameterBase

logger = logging.getLogger(__name__)


class TimeSeriesModel(ModelBase):
    def __init__(self) -> None:
        pass

    def add_parameter(self, parameter: ParameterBase[Any]) -> None:
        raise NotImplementedError

    # def add_ts_parameter(self, ts_parameter: ParameterTsBase[Any]) -> None:
    #     self._ts_parameters[ts_parameter.name] = ts_parameter

    # def add_const_parameter(self, const_parameter: ParameterBase[Any]) -> None:
    #     self._const_parameters[const_parameter.name] = const_parameter
