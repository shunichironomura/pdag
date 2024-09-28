from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ParameterBase[T]:
    name: str


@dataclass(frozen=True, slots=True)
class BooleanParameter(ParameterBase[bool]): ...


@dataclass(frozen=True, slots=True)
class NumericParameter(ParameterBase[float]):
    unit: str | None = field(default=None, kw_only=True)
    lower_bound: float | None = field(default=None, kw_only=True)
    upper_bound: float | None = field(default=None, kw_only=True)
