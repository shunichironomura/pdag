"""Poliynomials example to demonstrate how to include a model in another model."""

import pdag
from pdag.examples.polynomials import PolynomialModel


def test_model_name() -> None:
    assert PolynomialModel.name == "PolynomialModel"


def test_polynomial_model() -> None:
    core_model = PolynomialModel.to_core_model()
    exec_model = pdag.create_exec_model_from_core_model(core_model)
    results = pdag.execute_exec_model(
        exec_model,
        inputs={
            pdag.AbsoluteStaticParameterId("PolynomialModel", "a0"): 1.0,
            pdag.AbsoluteStaticParameterId("PolynomialModel", "a1"): 2.0,
            pdag.AbsoluteStaticParameterId("PolynomialModel", "a2"): 3.0,
            pdag.AbsoluteStaticParameterId("PolynomialModel", "x"): 4.0,
        },
    )

    assert results == {
        pdag.AbsoluteStaticParameterId("PolynomialModel", "a0"): 1.0,
        pdag.AbsoluteStaticParameterId("PolynomialModel", "a1"): 2.0,
        pdag.AbsoluteStaticParameterId("PolynomialModel", "a2"): 3.0,
        pdag.AbsoluteStaticParameterId("PolynomialModel", "x"): 4.0,
        pdag.AbsoluteStaticParameterId("PolynomialModel", "x_squared"): 4**2,
        pdag.AbsoluteStaticParameterId("PolynomialModel", "y"): 1 + 2 * 4 + 3 * 4**2,
        pdag.AbsoluteStaticParameterId("SquareModel", "x"): 4.0,
        pdag.AbsoluteStaticParameterId("SquareModel", "y"): 4**2,
    }
