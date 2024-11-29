from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import wraps
from itertools import chain
from typing import TYPE_CHECKING, Any

import networkx as nx

from ._base import ModelBase, ParameterBase
from ._node import CalculatedNode, InputNode, ParameterNode, RelationshipNode

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

    import pydot
    from matplotlib.axes import Axes

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Relationship:
    function: Callable[..., Any] = field(repr=False)
    inputs: tuple[ParameterBase[Any], ...]
    outputs: tuple[ParameterBase[Any], ...]


class Model(ModelBase):
    def __init__(self) -> None:
        self._nx_graph = nx.DiGraph()
        self._parameter_to_node: dict[ParameterBase[Any], ParameterNode[Any]] = {}
        self._parameters: dict[str, ParameterBase[Any]] = {}

    def _replace_node[T](self, old_node: ParameterNode[T], new_node: ParameterNode[T]) -> None:
        if old_node.parameter != new_node.parameter:
            msg = "Old and new nodes must have the same parameter."
            raise ValueError(msg)
        self._parameter_to_node[old_node.parameter] = new_node
        self._nx_graph.add_node(new_node)
        for predecessor in self._nx_graph.predecessors(old_node):
            self._nx_graph.add_edge(predecessor, new_node, **self._nx_graph.edges[predecessor, old_node])
        for successor in self._nx_graph.successors(old_node):
            self._nx_graph.add_edge(new_node, successor, **self._nx_graph.edges[old_node, successor])
        self._nx_graph.remove_node(old_node)

    @property
    def nx_graph(self) -> nx.DiGraph:
        return self._nx_graph

    def add_parameter(self, parameter: ParameterBase[Any]) -> None:
        if parameter in self._parameter_to_node:
            msg = f"Parameter {parameter} is already in the model."
            raise ValueError(msg)
        parameter_node = InputNode(parameter)
        self._parameters[parameter.name] = parameter
        self._parameter_to_node[parameter] = parameter_node
        self._nx_graph.add_node(parameter_node)

    def add_model(self, model: Model) -> None:
        input_parameters = tuple(model.iter_input_parameters())
        output_parameters = tuple(model.iter_output_parameters())
        for parameter in chain(input_parameters, output_parameters):
            self.add_parameter(parameter)

        def _function(*args: Any) -> tuple[Any, ...]:
            results = model.evaluate(dict(zip(input_parameters, args, strict=False)))
            return tuple(results[parameter] for parameter in output_parameters)

        self.add_relationship(_function, input_parameters, output_parameters)

    def add_relationship(  # noqa: C901
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

        for input_ in inputs:
            if input_ not in self._parameter_to_node:
                msg = f"Parameter {input_} is not in the model."
                raise ValueError(msg)
        for output in outputs:
            if output not in self._parameter_to_node:
                msg = f"Parameter {output} is not in the model."
                raise ValueError(msg)
            # if isinstance(self._parameter_to_node[output], InputNode):
            # raise ValueError(f"Parameter {output} is an input parameter.")  # noqa: ERA001
            if isinstance(self._parameter_to_node[output], CalculatedNode):
                msg = f"Calculation of parameter {output} is already defined."
                raise ValueError(msg)  # noqa: TRY004

        relationship_node = RelationshipNode(Relationship(_function, inputs, outputs))
        self._nx_graph.add_node(relationship_node)
        for input_ in inputs:
            self._nx_graph.add_edge(self._parameter_to_node[input_], relationship_node)
        for output in outputs:
            self._replace_node(self._parameter_to_node[output], self._parameter_to_node[output].as_calculated())
            self._nx_graph.add_edge(relationship_node, self._parameter_to_node[output])

    def is_evaluatable(self) -> bool:
        return True  # TODO: Implement

    def iter_parameters(self) -> Generator[ParameterBase[Any]]:
        for node in self._nx_graph.nodes:
            if isinstance(node, ParameterNode) and isinstance(node.parameter, ParameterBase):
                yield node.parameter

    def iter_input_parameters(self) -> Generator[ParameterBase[Any]]:
        for node in self._nx_graph.nodes:
            if isinstance(node, InputNode):
                yield node.parameter

    def iter_output_parameters(self) -> Generator[ParameterBase[Any]]:
        """Iterate over the output parameters of the model.

        All the calculated parameters are considered as output parameters for now.
        But we may need to mark only a subset of them as output parameters.
        """
        for node in self._nx_graph.nodes:
            if isinstance(node, CalculatedNode):
                yield node.parameter

    def evaluate(
        self,
        inputs: dict[ParameterBase[Any], Any],
    ) -> dict[ParameterBase[Any], Any]:
        results = {}
        memoized_evaluations = inputs.copy()
        for parameter in self.iter_parameters():
            logger.debug(f"Evaluating parameter: {parameter}")
            memoized_evaluations = self._update_memoized_evaluations_by_parameter_evaluation(
                parameter,
                memoized_evaluations,
            )
            results[parameter] = memoized_evaluations[parameter]

        return results

    def evaluate_parameter[T](
        self,
        parameter: ParameterBase[T],
        parameter_evaluations: dict[ParameterBase[Any], Any],
    ) -> T:
        memoized_evaluations = self._update_memoized_evaluations_by_parameter_evaluation(
            parameter,
            parameter_evaluations.copy(),
        )
        return memoized_evaluations[parameter]  # type: ignore[no-any-return]

    def _update_memoized_evaluations_by_parameter_evaluation(
        self,
        parameter: ParameterBase[Any],
        memoized_evaluations: dict[ParameterBase[Any], Any],
    ) -> dict[ParameterBase[Any], Any]:
        if parameter in memoized_evaluations:
            logger.debug(f"Parameter {parameter} is already in the memoized evaluations.")
            return memoized_evaluations

        parameter_node = self._parameter_to_node[parameter]
        try:
            relationship_node: RelationshipNode = next(
                iter(self._nx_graph.predecessors(parameter_node)),
            )  # Should be only one predecessor
        except StopIteration:
            msg = f"Parameter {parameter} is not in the memoized evaluations."
            raise ValueError(msg) from None

        dependency_nodes = list(self._nx_graph.predecessors(relationship_node))

        # If there is an incoming edge, the parameter has dependencies and must be evaluated recursively.
        for dependency_node in dependency_nodes:
            memoized_evaluations = self._update_memoized_evaluations_by_parameter_evaluation(
                dependency_node.parameter,
                memoized_evaluations,
            )

        logger.debug(f"Evaluating parameter {parameter} with relationship {relationship_node.relationship}")
        input_values = tuple(memoized_evaluations[dependency] for dependency in relationship_node.relationship.inputs)
        output_values = relationship_node.relationship.function(*input_values)
        for output, output_value in zip(relationship_node.relationship.outputs, output_values, strict=True):
            memoized_evaluations[output] = output_value

        return memoized_evaluations

    def draw_graph(self, ax: Axes | None = None) -> None:
        # Group nodes by type
        input_nodes = [node for node in self.nx_graph.nodes if isinstance(node, InputNode)]
        calculated_nodes = [node for node in self.nx_graph.nodes if isinstance(node, CalculatedNode)]
        relationship_nodes = [node for node in self.nx_graph.nodes if isinstance(node, RelationshipNode)]

        # Set subset_key for multipartite_layout
        for input_node in input_nodes:
            self.nx_graph.nodes[input_node]["subset"] = 0
        for calculated_node in calculated_nodes:
            self.nx_graph.nodes[calculated_node]["subset"] = 2
        for relationship_node in relationship_nodes:
            self.nx_graph.nodes[relationship_node]["subset"] = 1

        # pos = nx.spring_layout(self.nx_graph)  # noqa: ERA001
        pos = nx.multipartite_layout(self.nx_graph)

        # Draw nodes with different shapes and colors
        nx.draw_networkx_nodes(self.nx_graph, pos, nodelist=input_nodes, node_shape="^", ax=ax, node_color="r")
        nx.draw_networkx_nodes(self.nx_graph, pos, nodelist=calculated_nodes, node_shape="o", ax=ax, node_color="b")
        nx.draw_networkx_nodes(self.nx_graph, pos, nodelist=relationship_nodes, node_shape="s", ax=ax, node_color="g")

        # Draw edges
        nx.draw_networkx_edges(self.nx_graph, pos)

        # Draw labels
        nx.draw_networkx_labels(self.nx_graph, pos)

    def to_pydot(self) -> pydot.Dot:
        return nx.drawing.nx_pydot.to_pydot(self.nx_graph)
