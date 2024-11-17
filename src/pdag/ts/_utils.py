from dataclasses import dataclass

from ._parameter import ParameterTsBase


@dataclass(frozen=True, slots=True)
class DelayedParameterTs[T](ParameterTsBase[T]):
    parameter: ParameterTsBase[T]
    delay: int


@dataclass(frozen=True, slots=True)
class InitialValueParameter[T](ParameterTsBase[T]):
    parameter: ParameterTsBase[T]


def delayed[T](parameter: ParameterTsBase[T], *, delay: int = 1) -> DelayedParameterTs[T]:
    if delay > 1:
        msg = "Only delay of 1 is supported"
        raise NotImplementedError(msg)
    return DelayedParameterTs(name=parameter.name, parameter=parameter, delay=delay)


def initial[T](parameter: ParameterTsBase[T]) -> InitialValueParameter[T]:
    return InitialValueParameter(name=parameter.name, parameter=parameter)
