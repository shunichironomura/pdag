"""Poliynomials example to demonstrate how to include a model in another model."""

from typing import Annotated


import pdag
from pdag._exec.to_exec_model import create_exec_model_from_core_model
from pdag._exec.model import AbsoluteStaticParameterId
from pdag._exec.core import execute_exec_model


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


def test_model_name() -> None:
    assert PolynomialModel.name == "PolynomialModel"


def test_polynomial_model() -> None:
    core_model = PolynomialModel.to_core_model()
    exec_model = create_exec_model_from_core_model(core_model)
    results = execute_exec_model(
        exec_model,
        inputs={
            AbsoluteStaticParameterId("PolynomialModel", "a0"): 1.0,
            AbsoluteStaticParameterId("PolynomialModel", "a1"): 2.0,
            AbsoluteStaticParameterId("PolynomialModel", "a2"): 3.0,
            AbsoluteStaticParameterId("PolynomialModel", "x"): 4.0,
        },
    )

    assert results == {
        AbsoluteStaticParameterId("PolynomialModel", "a0"): 1.0,
        AbsoluteStaticParameterId("PolynomialModel", "a1"): 2.0,
        AbsoluteStaticParameterId("PolynomialModel", "a2"): 3.0,
        AbsoluteStaticParameterId("PolynomialModel", "x"): 4.0,
        AbsoluteStaticParameterId("PolynomialModel", "x_squared"): 4**2,
        AbsoluteStaticParameterId("PolynomialModel", "y"): 1 + 2 * 4 + 3 * 4**2,
        AbsoluteStaticParameterId("SquareModel", "x"): 4.0,
        AbsoluteStaticParameterId("SquareModel", "y"): 4**2,
    }
