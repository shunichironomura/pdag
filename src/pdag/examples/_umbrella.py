from typing import Annotated

import pdag


class UmbrellaModel(pdag.Model):
    """Evaluate which type of umbrella to take or not."""

    # Exogenous parameters
    rain_intensity = pdag.RealParameter(
        "rain_intensity",
        metadata={"XLRM": "X"},
        lower_bound=0.0,
        upper_bound=1.0,
    )

    # Levers
    policy = pdag.CategoricalParameter(
        "policy",
        ("take_umbrella", "take_travel_umbrella", "no_umbrella"),
        metadata={"XLRM": "L"},
    )

    # Performance metrics
    wetness = pdag.RealParameter(
        "wetness",
        metadata={"XLRM": "M"},
    )
    portability = pdag.RealParameter(
        "portability",
        metadata={"XLRM": "M"},
    )

    @pdag.relationship
    @staticmethod
    def calc_wetness(
        rain_intensity: Annotated[float, rain_intensity.ref()],
        policy: Annotated[str, policy.ref()],
    ) -> Annotated[float, wetness.ref()]:
        """Calculate the wetness based on the rain and policy."""
        match policy:
            case "take_umbrella":
                return rain_intensity * 0.1
            case "take_travel_umbrella":
                return rain_intensity * 0.2
            case "no_umbrella":
                return rain_intensity
            case _:
                msg = f"Unknown policy: {policy}"
                raise ValueError(msg)

    @pdag.relationship
    @staticmethod
    def calc_portability(
        policy: Annotated[str, policy.ref()],
    ) -> Annotated[float, portability.ref()]:
        """Calculate the portability based on the policy."""
        match policy:
            case "take_umbrella":
                return -1.0
            case "take_travel_umbrella":
                return -0.5
            case "no_umbrella":
                return 0.0
            case _:
                msg = f"Unknown policy: {policy}"
                raise ValueError(msg)


if __name__ == "__main__":
    from itertools import product

    import numpy as np
    from rich import print  # noqa: A004

    from pdag._experiment.multi_process import run_experiments
    from pdag._utils.random_string import generate_random_string

    core_model = UmbrellaModel.to_core_model()
    print("Core model:")
    print(core_model)

    exec_model = pdag.create_exec_model_from_core_model(core_model)
    print("Execution model:")
    print(exec_model)
    print("Input parameters:")
    print(exec_model.input_parameter_ids())

    # Run the model for one case
    results = pdag.execute_exec_model(
        exec_model,
        inputs={
            pdag.StaticParameterId((), "policy"): "take_umbrella",
            pdag.StaticParameterId((), "rain_intensity"): 0.5,
        },
    )
    print("Results:")
    print(results)

    # Run the model for multiple cases
    input_parameters = exec_model.input_parameters()
    scenario_parameters = {
        parameter_id: parameter
        for parameter_id, parameter in input_parameters.items()
        if parameter.metadata.get("XLRM", None) == "X"
    }
    decision_parameters = {
        parameter_id: parameter
        for parameter_id, parameter in input_parameters.items()
        if parameter.metadata.get("XLRM", None) == "L"
    }
    print("Scenario parameters:")
    print(scenario_parameters)
    print("Decision parameters:")
    print(decision_parameters)
    assert set(scenario_parameters) | set(decision_parameters) == set(input_parameters)

    n_scenarios = 100
    n_decisions = 100
    rng = np.random.default_rng(42)
    scenarios = pdag.distance_constrained_sampling(
        scenario_parameters,
        n_samples=n_scenarios,
        budget=1,
        rng=rng,
        uniform_in_distance=True,
    )
    decisions = pdag.sample_parameter_values(decision_parameters, n_samples=n_decisions, rng=rng)

    scenario_ids = [generate_random_string() for _ in range(n_scenarios)]
    decision_ids = [generate_random_string() for _ in range(n_decisions)]

    cases = (scenario | decision for scenario, decision in product(scenarios, decisions))
    metadata = (
        {"scenario_id": scenario_id, "decision_id": decision_id, "case_id": generate_random_string()}
        for scenario_id, decision_id in product(scenario_ids, decision_ids)
    )
    run_experiments(
        exec_model,
        cases,
        metadata=metadata,
        n_cases=n_scenarios * n_decisions,
        parquet_file_path="umbrella.parquet",
    )
