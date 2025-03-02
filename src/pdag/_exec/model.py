from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StaticParameterIdentifier:
    name: str


@dataclass(frozen=True, slots=True)
class TimeSeriesParameterIdentifier:
    name: str
    time_step: int


type ParameterIdentifier = StaticParameterIdentifier | TimeSeriesParameterIdentifier
