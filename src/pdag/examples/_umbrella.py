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
    from rich import print  # noqa: A004

    core_model = UmbrellaModel.to_core_model()
    print("Core model:")
    print(core_model)

    exec_model = pdag.create_exec_model_from_core_model(core_model)
    print("Execution model:")
    print(exec_model)
    print("Input parameters:")
    print(exec_model.input_parameter_ids())

    results = pdag.execute_exec_model(
        exec_model,
        inputs={
            pdag.StaticParameterId((), "policy"): "take_umbrella",
            pdag.StaticParameterId((), "rain_intensity"): 0.5,
        },
    )
    print("Results:")
    print(results)
