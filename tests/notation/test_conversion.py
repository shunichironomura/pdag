import ast
import inspect
from textwrap import dedent

import pytest

import pdag

from .cases import CASES_CORE_MODEL_TO_DC_NOTATION, CASES_DC_NOTATION_TO_CORE_MODEL


@pytest.mark.parametrize(("dc_notation", "core_model"), CASES_CORE_MODEL_TO_DC_NOTATION)
def test_core_model_to_dataclass_notation_by_ast(dc_notation: type[pdag.Model], core_model: pdag.CoreModel) -> None:
    dc_notation_source = dedent(inspect.getsource(dc_notation))

    # Compare AST
    class_def_constructed = pdag.core_model_to_dataclass_notation_ast(core_model)
    expected = ast.parse(dc_notation_source).body[0]
    assert ast.dump(class_def_constructed, indent=2) == ast.dump(expected, indent=2)


@pytest.mark.parametrize(("dc_notation", "core_model"), CASES_CORE_MODEL_TO_DC_NOTATION)
def test_core_model_to_dataclass_notation_by_source(dc_notation: type[pdag.Model], core_model: pdag.CoreModel) -> None:
    """This test is redundant, as it is essentially the same as test_core_model_to_dataclass_notation_by_ast.

    But it helps debug the conversion to source code.
    """
    dc_notation_source = dedent(inspect.getsource(dc_notation))

    # Compare unparsed source code
    source_constructed = pdag.core_model_to_content(core_model)
    assert source_constructed == ast.unparse(ast.parse(dc_notation_source))


@pytest.mark.parametrize(("dc_notation", "core_model"), CASES_DC_NOTATION_TO_CORE_MODEL)
def test_dataclass_notation_to_core_model(
    dc_notation: type[pdag.Model],
    core_model: pdag.CoreModel,
) -> None:
    # Compare CoreModel
    exported_core_model = dc_notation.to_core_model()
    assert exported_core_model == core_model
