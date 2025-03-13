"""Poliynomials example to demonstrate how to include a model in another model."""

from typing import Annotated

import numpy as np

import pdag


class SquareModel(pdag.Model):
    """Square model."""

    x = pdag.RealParameter("x")
    y = pdag.RealParameter("y")

    @pdag.relationship
    @staticmethod
    def square(*, x: Annotated[float, x.ref()]) -> Annotated[float, y.ref()]:  # noqa: D102
        return x**2


class PolynomialModel(pdag.Model):
    """Polynomial model."""

    a = pdag.Array("a", np.array([pdag.RealParameter(...) for _ in range(3)]))
    x = pdag.RealParameter("x")
    x_squared = pdag.RealParameter("x_squared")
    y = pdag.RealParameter("y")

    calc_square_term = SquareModel.to_relationship(
        "calc_square_term",
        inputs={SquareModel.x.ref(): x.ref()},
        outputs={SquareModel.y.ref(): x_squared.ref()},
    )

    @pdag.relationship
    @staticmethod
    def polynomial(  # noqa: D102
        *,
        a: Annotated[list[float], a.ref()],
        x: Annotated[float, x.ref()],
        x_squared: Annotated[float, x_squared.ref()],
    ) -> Annotated[float, y.ref()]:
        return a[0] + a[1] * x + a[2] * x_squared


if __name__ == "__main__":
    from rich import print  # noqa: A004

    core_model = PolynomialModel.to_core_model()
    print(core_model)
    exec_model = pdag.create_exec_model_from_core_model(core_model)
    print(exec_model)
