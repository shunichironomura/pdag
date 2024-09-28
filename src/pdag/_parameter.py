from abc import ABC


class ParameterBase[T](ABC):
    def __init__(
        self,
        name: str,
        /,
    ) -> None:
        self._name = name

    def __hash__(self) -> int:
        return hash(self._name)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ParameterBase):
            return NotImplemented
        return self._name == other._name

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._name!r})"

    def __str__(self) -> str:
        return self._name

    @property
    def name(self) -> str:
        return self._name


class BooleanParameter(ParameterBase[bool]):
    def __init__(
        self,
        name: str,
        /,
    ) -> None:
        super().__init__(name)

    def __hash__(self) -> int:
        return hash(self._name)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BooleanParameter):
            return NotImplemented
        return self._name == other._name


class NumericParameter(ParameterBase[float]):
    def __init__(
        self,
        name: str,
        /,
        *,
        unit: str | None = None,
        lower_bound: float | None = None,
        upper_bound: float | None = None,
    ) -> None:
        super().__init__(name)
        self._unit = unit
        self._lower_bound = lower_bound
        self._upper_bound = upper_bound

    def __hash__(self) -> int:
        return hash(self._name)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NumericParameter):
            return NotImplemented
        return (
            self._name == other._name
            and self._unit == other._unit
            and self._lower_bound == other._lower_bound
            and self._upper_bound == other._upper_bound
        )
