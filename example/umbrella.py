import xlrm
import networkx as nx


def main() -> None:
    model = xlrm.StaticModel()

    # External variables (X)
    is_raining = xlrm.BooleanVariable("Is it raining?", type="X")
    model.add_variable(is_raining)

    # Levers (L)
    will_take_umbrella = xlrm.BooleanVariable("Will I take an umbrella?", type="L")
    will_take_travel_umbrella = xlrm.BooleanVariable("Will I take a travel umbrella?", type="L")
    model.add_variable(will_take_umbrella)
    model.add_variable(will_take_travel_umbrella)

    # Performance metrics (M)
    wetness = xlrm.NumericVariable("Wetness", type="M", unit=None, lower_bound=0, upper_bound=1)
    convenience = xlrm.NumericVariable("Convenience", type="M", unit=None, lower_bound=0, upper_bound=1)
    model.add_variable(wetness)
    model.add_variable(convenience)

    # Relationships (R)
    # @xlrm.relationship((is_raining, will_take_umbrella, will_take_travel_umbrella), wetness)
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

    # @xlrm.relationship((will_take_umbrella, will_take_travel_umbrella), convenience)
    def how_convenient_will_it_be(will_take_umbrella: bool, will_take_travel_umbrella: bool) -> float:
        if will_take_umbrella:
            return 0
        elif will_take_travel_umbrella:
            return 0.5
        else:
            return 0

    # The relationship function can be None. In that case, the relationship is marked as unknown.
    model.add_relationship(how_convenient_will_it_be, (will_take_umbrella, will_take_travel_umbrella), convenience)

    graph = model.as_nx_graph()

    # Draw the graph
    import matplotlib.pyplot as plt

    pos = nx.spring_layout(graph)
    nx.draw(graph, pos, with_labels=True, arrows=True)
    plt.show()

    print(f"Model is evaluatable: {model.is_evaluatable()}")

    scenarios = model.sample_scenarios()
    decisions = model.sample_decisions()

    results = model.evaluate(scenarios, decisions)

    print(results)


if __name__ == "__main__":
    main()
