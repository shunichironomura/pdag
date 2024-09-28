from collections.abc import Generator
from typing import Any, Callable
import networkx as nx

from ._parameter import ParameterBase
from ._relationship import Relationship
from ._node import ParameterNode, InputNode, CalculatedNode, RelationshipNode
import logging

logger = logging.getLogger(__name__)


class Model:
    def __init__(self) -> None:
        self._nx_graph = nx.DiGraph()
        self._parameter_to_node: dict[ParameterBase[Any], ParameterNode[Any]] = {}

    def _replace_node[T](self, old_node: ParameterNode[T], new_node: ParameterNode[T]) -> None:
        if old_node.parameter != new_node.parameter:
            raise ValueError("Old and new nodes must have the same parameter.")
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
            raise ValueError(f"Parameter {parameter} is already in the model.")
        parameter_node = ParameterNode(parameter)
        self._parameter_to_node[parameter] = parameter_node
        self._nx_graph.add_node(parameter_node)

    def add_relationship(
        self,
        function: Callable[..., Any],
        inputs: tuple[ParameterBase[Any], ...] | ParameterBase[Any],
        outputs: tuple[ParameterBase[Any], ...] | ParameterBase[Any],
    ) -> None:
        if isinstance(inputs, ParameterBase):
            inputs = (inputs,)

        if isinstance(outputs, ParameterBase):
            outputs = (outputs,)

            def _function(*args: Any) -> Any:
                return (function(*args),)
        else:
            _function = function

        for input_ in inputs:
            if input_ not in self._parameter_to_node:
                raise ValueError(f"Parameter {input_} is not in the model.")
        for output in outputs:
            if output not in self._parameter_to_node:
                raise ValueError(f"Parameter {output} is not in the model.")
            if isinstance(self._parameter_to_node[output], InputNode):
                raise ValueError(f"Parameter {output} is an input parameter.")
            elif isinstance(self._parameter_to_node[output], CalculatedNode):
                raise ValueError(f"Calculation of parameter {output} is already defined.")

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

    def evaluate(
        self,
        inputs: dict[ParameterBase[Any], Any],
    ) -> dict[ParameterBase[Any], Any]:
        results = {}
        memoized_evaluations = inputs.copy()
        for parameter in self.iter_parameters():
            logger.debug(f"Evaluating parameter: {parameter}")
            memoized_evaluations = self._update_memoized_evaluations_by_parameter_evaluation(
                parameter, memoized_evaluations
            )
            results[parameter] = memoized_evaluations[parameter]

        return results

    def evaluate_parameter(
        self, parameter: ParameterBase[Any], parameter_evaluations: dict[ParameterBase[Any], Any]
    ) -> Any:
        memoized_evaluations = self._update_memoized_evaluations_by_parameter_evaluation(
            parameter, parameter_evaluations.copy()
        )
        return memoized_evaluations[parameter]

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
                iter(self._nx_graph.predecessors(parameter_node))
            )  # Should be only one predecessor
        except StopIteration:
            raise ValueError(f"Parameter {parameter} is not in the memoized evaluations.")

        dependency_nodes = list(self._nx_graph.predecessors(relationship_node))

        # If there is an incoming edge, the parameter has dependencies and must be evaluated recursively.
        for dependency_node in dependency_nodes:
            memoized_evaluations = self._update_memoized_evaluations_by_parameter_evaluation(
                dependency_node.parameter, memoized_evaluations
            )

        logger.debug(f"Evaluating parameter {parameter} with relationship {relationship_node.relationship}")
        input_values = tuple(memoized_evaluations[dependency] for dependency in relationship_node.relationship.inputs)
        # parameter_output_index = relationship.outputs.index(parameter)
        output_values = relationship_node.relationship.function(*input_values)
        for output, output_value in zip(relationship_node.relationship.outputs, output_values, strict=True):
            memoized_evaluations[output] = output_value

        return memoized_evaluations
