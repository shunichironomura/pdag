import ast
import inspect
from textwrap import dedent
from typing import Annotated, Literal

import pytest

import pdag


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


square_root_core_model = pdag.CoreModel(
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
            evaluated_at_each_time_step=False,
        ),
    },
)

CASES = [
    (SquareRootModel, square_root_core_model),
]


@pytest.mark.parametrize(("dc_notation", "core_model"), CASES)
def test_core_model_to_dataclass_notation_by_ast(dc_notation: type[pdag.Model], core_model: pdag.CoreModel) -> None:
    dc_notation_source = dedent(inspect.getsource(dc_notation))

    # Compare AST
    class_def_constructed = pdag.core_model_to_dataclass_notation_ast(core_model)
    expected = ast.parse(dc_notation_source).body[0]
    assert ast.dump(class_def_constructed, indent=2) == ast.dump(expected, indent=2)


@pytest.mark.parametrize(("dc_notation", "core_model"), CASES)
def test_core_model_to_dataclass_notation_by_source(dc_notation: type[pdag.Model], core_model: pdag.CoreModel) -> None:
    """This test is redundant, as it is essentially the same as test_core_model_to_dataclass_notation_by_ast.

    But it helps debug the conversion to source code.
    """
    dc_notation_source = dedent(inspect.getsource(dc_notation))

    # Compare unparsed source code
    source_constructed = pdag.core_model_to_content(core_model)
    assert source_constructed == ast.unparse(ast.parse(dc_notation_source))


@pytest.mark.parametrize(("dc_notation", "core_model"), CASES)
def test_dataclass_notation_to_core_model(
    dc_notation: type[pdag.Model],
    core_model: pdag.CoreModel,
) -> None:
    # Compare CoreModel
    exported_core_model = dc_notation.to_core_model()
    assert exported_core_model == core_model
