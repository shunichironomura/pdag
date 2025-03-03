"""Poliynomials example to demonstrate how to include a model in another model."""

from typing import Annotated

import pdag


class SquareModel(pdag.Model):
    """Square model."""

    x = pdag.RealParameter("x")
    y = pdag.RealParameter("y")

    @pdag.relationship
    @staticmethod
    def square(*, x: Annotated[float, pdag.ParameterRef("x")]) -> Annotated[float, pdag.ParameterRef("y")]:  # noqa: D102
        return x**2


class PolynomialModel(pdag.Model):
    """Polynomial model."""

    a0 = pdag.RealParameter("a0")
    a1 = pdag.RealParameter("a1")
    a2 = pdag.RealParameter("a2")
    x = pdag.RealParameter("x")
    x_squared = pdag.RealParameter("x_squared")
    y = pdag.RealParameter("y")

    calc_square_term = SquareModel.to_relationship(
        "calc_square_term",
        inputs={pdag.ParameterRef("x"): pdag.ParameterRef("x")},
        outputs={pdag.ParameterRef("y"): pdag.ParameterRef("x_squared")},
    )

    @pdag.relationship
    @staticmethod
    def polynomial(  # noqa: D102
        *,
        a0: Annotated[float, pdag.ParameterRef("a0")],
        a1: Annotated[float, pdag.ParameterRef("a1")],
        a2: Annotated[float, pdag.ParameterRef("a2")],
        x: Annotated[float, pdag.ParameterRef("x")],
        x_squared: Annotated[float, pdag.ParameterRef("x_squared")],
    ) -> Annotated[float, pdag.ParameterRef("y")]:
        return a0 + a1 * x + a2 * x_squared


if __name__ == "__main__":
    from rich import print  # noqa: A004

    from pdag._exec import exec_core_model_via_paramref as exec_core_model

    core_model = PolynomialModel.to_core_model()
    print(core_model)
    results = exec_core_model(
        core_model,
        inputs={
            pdag.ParameterRef("a0"): 1.0,
            pdag.ParameterRef("a1"): 2.0,
            pdag.ParameterRef("a2"): 3.0,
            pdag.ParameterRef("x"): 4.0,
        },
    )
