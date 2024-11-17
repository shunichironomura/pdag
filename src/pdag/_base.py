from __future__ import annotations

import queue
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import TracebackType


class ModelBase(ABC):
    _thread_local = threading.local()

    @classmethod
    def _get_run_stack(cls) -> queue.LifoQueue[Self]:
        if not hasattr(cls._thread_local, "run_stack"):
            cls._thread_local.run_stack = queue.LifoQueue()
        return cls._thread_local.run_stack  # type: ignore[no-any-return]

    @classmethod
    def context_is_active(cls) -> bool:
        if not hasattr(cls._thread_local, "run_stack"):
            return False
        return cls._thread_local.run_stack.qsize() > 0  # type: ignore[no-any-return]

    @classmethod
    def get_current(cls) -> Self:
        try:
            return cls._get_run_stack().queue[-1]
        except IndexError as e:
            msg = "Cannot get the current model"
            raise ValueError(msg) from e

    def __enter__(self) -> Self:
        self._get_run_stack().put(self, block=False)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._get_run_stack().get(block=False)

    @abstractmethod
    def add_parameter(self, parameter: ParameterBase[Any]) -> None:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class ParameterBase[T]:
    name: str

    def __post_init__(self) -> None:
        if ModelBase.context_is_active():
            active_model = ModelBase.get_current()
            active_model.add_parameter(self)

    def __repr__(self) -> str:
        return self.name


@dataclass(frozen=True, slots=True)
class Relationship:
    function: Callable[..., Any] = field(repr=False)
    inputs: tuple[ParameterBase[Any], ...]
    outputs: tuple[ParameterBase[Any], ...]
