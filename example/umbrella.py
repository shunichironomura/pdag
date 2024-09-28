import logging
import pdag

from rich.logging import RichHandler
from itertools import product

logger = logging.getLogger(__name__)


def main() -> None:
    model = pdag.Model()

    # External parameters (X)
    is_raining = pdag.BooleanParameter("Is it raining?")
    model.add_parameter(is_raining)

    # Levers (L)
    will_take_umbrella = pdag.BooleanParameter("Will I take an umbrella?")
    will_take_travel_umbrella = pdag.BooleanParameter("Will I take a travel umbrella?")
    model.add_parameter(will_take_umbrella)
    model.add_parameter(will_take_travel_umbrella)

    # Performance metrics (M)
    wetness = pdag.NumericParameter("Wetness", unit=None, lower_bound=0, upper_bound=1)
    convenience = pdag.NumericParameter("Convenience", unit=None, lower_bound=0, upper_bound=1)
    model.add_parameter(wetness)
    model.add_parameter(convenience)

    # Relationships (R)
    # @pdag.relationship((is_raining, will_take_umbrella, will_take_travel_umbrella), wetness)
    def how_wet_will_i_get(is_raining: bool, will_take_umbrella: bool, will_take_travel_umbrella: bool) -> float:
        if is_raining:
            if will_take_umbrella:
                return 0
            elif will_take_travel_umbrella:
                return 0.5
            else:
                return 1
        else:
            return 0

    model.add_relationship(how_wet_will_i_get, (is_raining, will_take_umbrella, will_take_travel_umbrella), wetness)

    # @pdag.relationship((will_take_umbrella, will_take_travel_umbrella), convenience)
    def how_convenient_will_it_be(will_take_umbrella: bool, will_take_travel_umbrella: bool) -> float:
        convenience = 0.0

        if will_take_umbrella:
            convenience -= 1.0

        if will_take_travel_umbrella:
            convenience -= 0.5

        return convenience

    # The relationship function can be None. In that case, the relationship is marked as unknown.
    model.add_relationship(how_convenient_will_it_be, (will_take_umbrella, will_take_travel_umbrella), convenience)

    # # Draw the graph
    # import matplotlib.pyplot as plt

    # pos = nx.spring_layout(model.nx_graph)
    # nx.draw(model.nx_graph, pos, with_labels=True, arrows=True)
    # plt.show()

    logger.info(f"Model is evaluatable: {model.is_evaluatable()}")

    scenarios = [
        {is_raining: True},
        {is_raining: False},
    ]
    logger.info(f"Scenarios: {scenarios}")

    decisions = [
        {
            will_take_umbrella: will_take_umbrella_value,
            will_take_travel_umbrella: will_take_travel_umbrella_value,
        }
        for will_take_umbrella_value, will_take_travel_umbrella_value in product([True, False], repeat=2)
    ]
    logger.info(f"Decisions: {decisions}")

    inputs = [scenario | decision for scenario, decision in product(scenarios, decisions)]

    results = [model.evaluate(input) for input in inputs]  # type: ignore[arg-type] # TODO: Fix this type error
    logger.info(f"Results: {results}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)],
    )
    main()
