import ast
from textwrap import dedent
from typing import Annotated, Literal

import pytest

import pdag


@pytest.fixture
def square_root_model():  # type:ignore[no-untyped-def]
    class SquareRootModel(pdag.Model):
        """A model for square root."""

        x = pdag.RealParameter("x")
        y = pdag.RealParameter("y")
        z = pdag.CategoricalParameter("z", categories={"pos", "neg"})

        @pdag.relationship
        @staticmethod
        def sqrt(
            *,
            x_arg: Annotated[float, pdag.ParameterRef("x")],
            z_arg: Annotated[Literal["neg", "pos"], pdag.ParameterRef("z")],
        ) -> Annotated[float, pdag.ParameterRef("y")]:
            if z_arg == "pos":
                return float(x_arg**0.5)
            return -float(x_arg**0.5)

    return SquareRootModel


_SQUARE_ROOT_MODEL_SOURCE = """\
class SquareRootModel(pdag.Model):
    x = pdag.RealParameter("x")
    y = pdag.RealParameter("y")
    z = pdag.CategoricalParameter("z", categories={"pos", "neg"})

    @pdag.relationship
    @staticmethod
    def sqrt(
        *,
        x_arg: Annotated[float, pdag.ParameterRef("x")],
        z_arg: Annotated[Literal["pos", "neg"], pdag.ParameterRef("z")],
    ) -> Annotated[float, pdag.ParameterRef("y")]:
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
            "z": pdag.CategoricalParameter("z", categories={"pos", "neg"}),
        },
        collections={},
        relationships={
            "sqrt": pdag.FunctionRelationship(
                name="sqrt",
                inputs={"x_arg": pdag.ParameterRef("x"), "z_arg": pdag.ParameterRef("z")},
                outputs=[pdag.ParameterRef("y")],
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


def test_core_model_to_dataclass_notation_by_ast(square_root_core_model: pdag.CoreModel) -> None:
    # Compare AST
    class_def_constructed = pdag.core_model_to_dataclass_notation_ast(square_root_core_model)
    expected = ast.parse(_SQUARE_ROOT_MODEL_SOURCE).body[0]
    assert ast.dump(class_def_constructed, indent=2) == ast.dump(expected, indent=2)


def test_core_model_to_dataclass_notation_by_source(square_root_core_model: pdag.CoreModel) -> None:
    """This test is redundant, as it is essentially the same as test_core_model_to_dataclass_notation_by_ast.

    But it helps debug the conversion to source code.
    """
    # Compare unparsed source code
    source_constructed = pdag.core_model_to_content(square_root_core_model)
    assert source_constructed == ast.unparse(ast.parse(_SQUARE_ROOT_MODEL_SOURCE))


def test_dataclass_notation_to_core_model(
    square_root_model: pdag.Model,
    square_root_core_model: pdag.CoreModel,
) -> None:
    # Compare CoreModel
    exported_core_model = square_root_model.to_core_model()
    assert exported_core_model == square_root_core_model
