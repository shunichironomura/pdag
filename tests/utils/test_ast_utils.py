import pytest

from pdag._utils import get_function_body


def test_get_function_body() -> None:
    def sample_function() -> None:
        return None

    body = get_function_body(sample_function)
    assert body == "return None\n"


@pytest.mark.xfail(reason="Cannot extract the comment if it is the first line of the function body.")
def test_get_function_body_starting_with_comment() -> None:
    def sample_function() -> None:
        # This is a comment
        return None

    body = get_function_body(sample_function)
    assert body == "# This is a comment\nreturn None\n"


def test_get_function_body_with_comment() -> None:
    def sample_function() -> int:
        x = 0

        # This is a comment
        return x + 1

    body = get_function_body(sample_function)
    assert body == "x = 0\n\n# This is a comment\nreturn x + 1\n"


def test_get_function_body_with_docstring() -> None:
    def sample_function() -> int:
        """This is a docstring."""
        return 1

    body = get_function_body(sample_function)
    assert body == '"""This is a docstring."""\nreturn 1\n'
