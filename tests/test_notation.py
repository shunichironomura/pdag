import ast
from textwrap import dedent
from typing import Annotated, Literal

import pytest

import pdag


@pytest.fixture
def square_root_model():  # type:ignore[no-untyped-def]
    class SquareRootModel(pdag.Model):
        """A model for square root."""

        x: Annotated[float, pdag.RealParameter("x")]
        y: Annotated[float, pdag.RealParameter("y")]
        z: Annotated[Literal["neg", "pos"], pdag.CategoricalParameter("z", categories=frozenset({"pos", "neg"}))]

        @pdag.relationship
        @staticmethod
        def sqrt(
            *,
            x_arg: Annotated[float, pdag.Parameter("x")],
            z_arg: Annotated[Literal["neg", "pos"], pdag.Parameter("z")],
        ) -> Annotated[float, pdag.Parameter("y")]:
            if z_arg == "pos":
                return float(x_arg**0.5)
            return -float(x_arg**0.5)

    return SquareRootModel


_SQUARE_ROOT_MODEL_SOURCE = """\
class SquareRootModel(pdag.Model):
    x: Annotated[float, pdag.RealParameter("x")]
    y: Annotated[float, pdag.RealParameter("y")]
    z: Annotated[Literal["pos", "neg"], pdag.CategoricalParameter("z", categories=frozenset({"pos", "neg"}))]

    @pdag.relationship
    @staticmethod
    def sqrt(
        *,
        x_arg: Annotated[float, pdag.Parameter("x")],
        z_arg: Annotated[Literal["pos", "neg"], pdag.Parameter("z")],
    ) -> Annotated[float, pdag.Parameter("y")]:
        if z_arg == "pos":
            return float(x_arg**0.5)
        return -float(x_arg**0.5)
"""


@pytest.fixture
def square_root_core_model() -> pdag.CoreModel:
    return pdag.CoreModel(
        name="SquareRootModel",
        parameters={
            "x": pdag.RealParameter("x"),
            "y": pdag.RealParameter("y"),
            "z": pdag.CategoricalParameter("z", categories=frozenset({"pos", "neg"})),
        },
        collections={},
        relationships={
            "sqrt": pdag.FunctionRelationship(
                name="sqrt",
                inputs={"x_arg": "x", "z_arg": "z"},
                outputs=["y"],
                output_is_scalar=True,
                function_body=dedent(
                    """\
                    if z_arg == "pos":
                        return float(x_arg**0.5)
                    return -float(x_arg**0.5)
                    """,
                ),
            ),
        },
    )


def test_core_model_to_dataclass_notation(square_root_core_model: pdag.CoreModel) -> None:
    # Compare AST
    class_def_constructed = pdag.core_model_to_dataclass_notation_ast(square_root_core_model)
    expected = ast.parse(_SQUARE_ROOT_MODEL_SOURCE).body[0]
    assert ast.dump(class_def_constructed, indent=2) == ast.dump(expected, indent=2)


def test_dataclass_notation_to_core_model(
    square_root_model: pdag.Model,
    square_root_core_model: pdag.CoreModel,
) -> None:
    # Compare CoreModel
    exported_core_model = square_root_model.to_core_model()
    assert exported_core_model == square_root_core_model
