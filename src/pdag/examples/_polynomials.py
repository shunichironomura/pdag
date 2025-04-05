from typing import Annotated

import numpy as np

import pdag

from ._square import SquareModel


class PolynomialModel(pdag.Model):
    """Polynomial model to demonstrate how to include a model in another model.

    This model calculates a polynomial `y = a[0] + a[1] * x + a[2] * x^2`
    where a[0], a[1], and a[2] are coefficients of the polynomial.
    """

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
    def polynomial(
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
