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
            pdag.StaticParameterId((), "a[0]"): 1.0,
            pdag.StaticParameterId((), "a[1]"): 2.0,
            pdag.StaticParameterId((), "a[2]"): 3.0,
            pdag.StaticParameterId((), "x"): 4.0,
        },
    )

    assert results == {
        pdag.StaticParameterId((), "a[0]"): 1.0,
        pdag.StaticParameterId((), "a[1]"): 2.0,
        pdag.StaticParameterId((), "a[2]"): 3.0,
        pdag.StaticParameterId((), "x"): 4.0,
        pdag.StaticParameterId((), "x_squared"): 4**2,
        pdag.StaticParameterId((), "y"): 1 + 2 * 4 + 3 * 4**2,
        pdag.StaticParameterId(("calc_square_term",), "x"): 4.0,
        pdag.StaticParameterId(("calc_square_term",), "y"): 4**2,
    }
