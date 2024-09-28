from collections.abc import Generator
import numpy as np
from typing import Any, Callable, Literal
import networkx as nx
from ._variable import VariableBase
from ._relationship import Relationship
import logging
import numpy.typing as npt

logger = logging.getLogger(__name__)


class StaticModel:
    def __init__(self) -> None:
        self._nx_graph = nx.DiGraph()

    @property
    def nx_graph(self) -> nx.DiGraph:
        return self._nx_graph

    def add_variable(self, variable: VariableBase[Any]) -> None:
        self._nx_graph.add_node(variable)

    def add_relationship(
        self,
        function: Callable[..., Any],
        inputs: tuple[VariableBase[Any], ...] | VariableBase[Any],
        outputs: tuple[VariableBase[Any], ...] | VariableBase[Any],
    ) -> None:
        if isinstance(inputs, VariableBase):
            inputs = (inputs,)

        if isinstance(outputs, VariableBase):
            outputs = (outputs,)

            def _function(*args: Any) -> Any:
                return (function(*args),)
        else:
            _function = function

        for input_ in inputs:
            if input_ not in self._nx_graph.nodes:
                raise ValueError(f"Variable {input_} is not in the model.")
        for output in outputs:
            if output not in self._nx_graph.nodes:
                raise ValueError(f"Variable {output} is not in the model.")

        for output in outputs:
            incoming_edges = set(self._nx_graph.predecessors(output))
            if incoming_edges:
                raise ValueError(f"Variable {output} already has incoming edges.")

        for input_ in inputs:
            for output in outputs:
                self._nx_graph.add_edge(input_, output, relationship=Relationship(_function, inputs, outputs))

    def is_evaluatable(self) -> bool:
        return True  # TODO: Implement

    def iter_variables(self, type: Literal["X", "L", "M"] | None = None) -> Generator[VariableBase[Any]]:
        for variable in self._nx_graph.nodes:
            if type is None or variable.type == type:
                yield variable

    def sample_scenarios(
        self,
        *,
        size: int | tuple[int, ...] | None = None,
        rng: np.random.Generator | None = None,
    ) -> dict[VariableBase[Any], npt.NDArray[Any]]:
        x_variables = list(self.iter_variables("X"))

        if rng is None:
            rng = np.random.default_rng()
        return {x_variable: x_variable.sample(size=size, rng=rng) for x_variable in x_variables}

    def sample_decisions(
        self,
        *,
        size: int | tuple[int, ...] | None = None,
        rng: np.random.Generator | None = None,
    ) -> dict[VariableBase[Any], npt.NDArray[Any]]:
        l_variables = list(self.iter_variables("L"))

        if rng is None:
            rng = np.random.default_rng()
        return {l_variable: l_variable.sample(size=size, rng=rng) for l_variable in l_variables}

    def evaluate(
        self, scenarios: dict[VariableBase[Any], npt.NDArray[Any]], decisions: dict[VariableBase[Any], npt.NDArray[Any]]
    ) -> dict[VariableBase[Any], npt.NDArray[Any]]:
        scenarios_shape = next(iter(scenarios.values())).shape
        assert all(scenario.shape == scenarios_shape for scenario in scenarios.values())
        logger.debug(f"Scenarios shape: {scenarios_shape}")

        decisions_shape = next(iter(decisions.values())).shape
        assert all(decision.shape == decisions_shape for decision in decisions.values())
        logger.debug(f"Decisions shape: {decisions_shape}")

        cases_shape = scenarios_shape + decisions_shape
        logger.debug(f"Cases shape: {cases_shape}")

        results = {variable: np.empty(cases_shape) for variable in self.iter_variables()}
        for case in np.ndindex(cases_shape):
            logger.debug(f"Evaluating case: {case}")
            case_scenario = {variable: scenarios[variable][case[: len(scenarios_shape)]] for variable in scenarios}
            case_decision = {variable: decisions[variable][case[len(scenarios_shape) :]] for variable in decisions}
            memoized_evaluations = case_scenario | case_decision
            for variable in self.iter_variables():
                logger.debug(f"Evaluating variable: {variable} in case: {case}")
                memoized_evaluations = self._update_memoized_evaluations_by_variable_evaluation(
                    variable, memoized_evaluations
                )
                results[variable][case] = memoized_evaluations[variable]

        return results

    def evaluate_variable(self, variable: VariableBase[Any], variable_evaluations: dict[VariableBase[Any], Any]) -> Any:
        memoized_evaluations = self._update_memoized_evaluations_by_variable_evaluation(
            variable, variable_evaluations.copy()
        )
        return memoized_evaluations[variable]

    def _update_memoized_evaluations_by_variable_evaluation(
        self,
        variable: VariableBase[Any],
        memoized_evaluations: dict[VariableBase[Any], Any],
    ) -> dict[VariableBase[Any], Any]:
        if variable in memoized_evaluations:
            logger.debug(f"Variable {variable} is already in the memoized evaluations.")
            return memoized_evaluations

        dependencies = set(self._nx_graph.predecessors(variable))
        # If there is no incoming edge, the variable has no dependencies and should be in the memoized evaluations.
        if not dependencies:
            raise ValueError(f"Variable {variable} is not in the memoized evaluations.")

        # If there is an incoming edge, the variable has dependencies and must be evaluated recursively.
        for dependency in dependencies:
            memoized_evaluations = self._update_memoized_evaluations_by_variable_evaluation(
                dependency, memoized_evaluations
            )

        relationship: Relationship = self._nx_graph.edges[next(iter(dependencies)), variable]["relationship"]
        logger.debug(f"Evaluating variable {variable} with relationship {relationship}")
        input_values = tuple(memoized_evaluations[dependency] for dependency in relationship.inputs)
        # variable_output_index = relationship.outputs.index(variable)
        output_values = relationship.function(*input_values)
        for output, output_value in zip(relationship.outputs, output_values, strict=True):
            memoized_evaluations[output] = output_value

        return memoized_evaluations
