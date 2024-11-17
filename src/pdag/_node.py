from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._base import ParameterBase, Relationship


class ParameterNode[T]:
    def __init__(self, parameter: ParameterBase[T]) -> None:
        self._parameter = parameter

    def __hash__(self) -> int:
        return hash(self._parameter)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ParameterNode):
            return NotImplemented
        return self._parameter == other._parameter

    def as_calculated(self) -> CalculatedNode[T]:
        return CalculatedNode(self._parameter)

    @property
    def parameter(self) -> ParameterBase[T]:
        return self._parameter

    def __repr__(self) -> str:
        return self._parameter.name


# All nodes that are not CalculatedNode are InputNode.
class InputNode[T](ParameterNode[T]):
    def __init__(self, parameter: ParameterBase[T]) -> None:
        super().__init__(parameter)

    def __hash__(self) -> int:
        return hash(self._parameter)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, InputNode):
            return NotImplemented
        return self._parameter == other._parameter


class CalculatedNode[T](ParameterNode[T]):
    def __init__(self, parameter: ParameterBase[T]) -> None:
        super().__init__(parameter)

    def __hash__(self) -> int:
        return hash(self._parameter)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CalculatedNode):
            return NotImplemented
        return self._parameter == other._parameter


class RelationshipNode:
    def __init__(self, relationship: Relationship) -> None:
        self._relationship = relationship

    def __hash__(self) -> int:
        return hash(self._relationship)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RelationshipNode):
            return NotImplemented
        return self._relationship == other._relationship

    @property
    def relationship(self) -> Relationship:
        return self._relationship

    def __repr__(self) -> str:
        return self._relationship.function.__name__


class ModelNode(RelationshipNode): ...


class OutputNode: ...
