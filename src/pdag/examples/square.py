"""Minimal example of a pdag model that squares a number."""

from typing import Annotated

import pdag


class SquareModel(pdag.Model):
    """Square model that squares a number."""

    # x is a real number parameter and is the input to the model
    x = pdag.RealParameter("x")

    # y is a real number parameter and is the output of the model
    y = pdag.RealParameter("y")

    # The relationship is defined as a static method
    # with the @pdag.relationship decorator
    @pdag.relationship
    @staticmethod
    def square(
        # The annotation `x.ref()` indicates that the value of `x` will be provided
        # as the value of the `x_arg` parameter when the model is executed.
        x_arg: Annotated[float, x.ref()],
        # The annotation `y.ref()` indicates that the return value of the method
        # will be assigned to the `y` parameter when the model is executed.
    ) -> Annotated[float, y.ref()]:
        """Square the input value."""
        return x_arg**2


if __name__ == "__main__":
    from rich import print  # noqa: A004

    core_model = SquareModel.to_core_model()
    exec_model = pdag.create_exec_model_from_core_model(core_model)
    results = pdag.execute_exec_model(
        exec_model,
        inputs={
            pdag.StaticParameterId((), "x"): 2.0,
        },
    )

    print(results)
