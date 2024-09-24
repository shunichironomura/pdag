from collections.abc import Generator
import numpy as np
from typing import Any, Callable
import networkx as nx
from ._variable import VariableBase
from ._relationship import Relationship

import numpy.typing as npt


class StaticModel:
    def __init__(self) -> None:
        self._variables: list[VariableBase[Any]] = []
        self._relationships: list[Relationship] = []

    def add_variable(self, variable: VariableBase[npt.NDArray[Any]]) -> None:
        self._variables.append(variable)

    def add_relationship(
        self,
        relationship: Callable[..., Any],
        inputs: tuple[VariableBase[npt.NDArray[Any]], ...] | VariableBase[npt.NDArray[Any]],
        outputs: tuple[VariableBase[npt.NDArray[Any]], ...] | VariableBase[npt.NDArray[Any]],
    ) -> None:
        if isinstance(inputs, VariableBase):
            inputs = (inputs,)
        if isinstance(outputs, VariableBase):
            outputs = (outputs,)

        for input_ in inputs:
            if input_ not in self._variables:
                raise ValueError(f"Variable {input_} is not in the model.")
        for output in outputs:
            if output not in self._variables:
                raise ValueError(f"Variable {output} is not in the model.")

        self._relationships.append(Relationship(relationship, inputs, outputs))

    def as_nx_graph(self) -> nx.DiGraph:
        graph = nx.DiGraph()

        for variable in self._variables:
            graph.add_node(variable)

        for relationship in self._relationships:
            for input_ in relationship.inputs:
                for output in relationship.outputs:
                    graph.add_edge(input_, output)

        return graph

    def is_evaluatable(self) -> bool:
        return True  # TODO: Implement

    def iter_x_nodes(self) -> Generator[VariableBase[Any]]:
        for variable in self._variables:
            if variable.type == "X":
                yield variable

    def iter_l_nodes(self) -> Generator[VariableBase[Any]]:
        for variable in self._variables:
            if variable.type == "L":
                yield variable

    def sample_scenarios(
        self,
        *,
        size: int | tuple[int, ...] | None = None,
        rng: np.random.Generator | None = None,
    ) -> dict[str, npt.NDArray[Any]]:
        x_nodes = list(self.iter_x_nodes())

        if rng is None:
            rng = np.random.default_rng()
        return {x_node.name: x_node.sample(size=size, rng=rng) for x_node in x_nodes}

    def sample_decisions(
        self,
        *,
        size: int | tuple[int, ...] | None = None,
        rng: np.random.Generator | None = None,
    ) -> dict[str, npt.NDArray[Any]]:
        l_nodes = list(self.iter_l_nodes())

        if rng is None:
            rng = np.random.default_rng()
        return {l_node.name: l_node.sample(size=size, rng=rng) for l_node in l_nodes}

    def evaluate(
        self, scenarios: dict[str, npt.NDArray[Any]], decisions: dict[str, npt.NDArray[Any]]
    ) -> dict[str, npt.NDArray[Any]]:
        raise NotImplementedError
