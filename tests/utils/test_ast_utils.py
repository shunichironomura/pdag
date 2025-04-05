from typing import Annotated, Literal

import pytest

import pdag
from pdag._utils import get_function_body


def sample_function() -> None:
    return None


def test_get_function_body() -> None:
    body = get_function_body(sample_function)
    assert body == "return None\n"


class SampleClass(pdag.Model):
    @staticmethod
    def sqrt(
        *,
        x_arg: Annotated[float, pdag.ParameterRef("x")],
        z_arg: Annotated[Literal["pos", "neg"], pdag.ParameterRef("z")],
    ) -> Annotated[float, pdag.ParameterRef("y")]:
        if z_arg == "pos":
            return float(x_arg**0.5)
        return -float(x_arg**0.5)


def test_get_function_body_method() -> None:
    body = get_function_body(SampleClass.sqrt)
    assert body == 'if z_arg == "pos":\n    return float(x_arg**0.5)\nreturn -float(x_arg**0.5)\n'


def sample_function_starting_with_comment() -> None:
    # This is a comment
    return None


@pytest.mark.xfail(reason="Cannot extract the comment if it is the first line of the function body.")
def test_get_function_body_starting_with_comment() -> None:
    body = get_function_body(sample_function_starting_with_comment)
    assert body == "# This is a comment\nreturn None\n"


def sample_function_with_comment() -> int:
    x = 0

    # This is a comment
    return x + 1


def test_get_function_body_with_comment() -> None:
    body = get_function_body(sample_function_with_comment)
    assert body == "x = 0\n\n# This is a comment\nreturn x + 1\n"


def sample_function_with_docstring() -> int:
    """This is a docstring."""
    return 1


def test_get_function_body_with_docstring() -> None:
    body = get_function_body(sample_function_with_docstring)
    assert body == '"""This is a docstring."""\nreturn 1\n'
