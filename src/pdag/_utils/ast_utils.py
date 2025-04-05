import ast
import inspect
from collections.abc import Callable
from textwrap import dedent
from typing import Any

import asttokens


def _guess_indentation(source: str) -> str:
    """Guess the indentation of the source code."""
    lines = source.splitlines()
    if not lines:
        msg = "Source code is empty."
        raise ValueError(msg)
    # Find the first non-empty line that starts with a non-whitespace character.
    for line in lines:
        if (
            # Not empty
            line.strip()
            # Not a comment
            and not line.lstrip().startswith("#")
            # Indented
            and (line.startswith((" ", "\t")))
        ):
            break
    else:
        msg = "Cannot guess indentation: all lines are empty or comments or non-indented."
        raise ValueError(msg)
    # Guess the indentation based on the first non-empty line.
    return line[: len(line) - len(line.lstrip())]


def get_function_body(func: Callable[..., Any]) -> str:
    r'''Get the body of a function as a string.

    For example, given a function:
    ```python
    def sample_function() -> None:
        return None
    ```

    `get_function_body(sample_function)` will return:
    ```python
    "return None\n"
    ```

    !!! note
        Currently, it cannot extract the comment if it is the first line of the function body.

        For example, given a function:
        ```python
        def sample_function() -> None:
            # This is a comment
            return None
        ```

        `get_function_body(sample_function)` will return:
        ```python
        "return None\n"
        ```

        It can, however, extract the docstring. For example, given a function:
        ```python
        def sample_function() -> int:
            """This is a docstring."""
            return 1
        ```
        `get_function_body(sample_function)` will return:
        ```python
        '"""This is a docstring."""\nreturn 1\n'
        ```

    '''
    source = dedent(inspect.getsource(func))
    # Parse the source with asttokens to keep track of positions.
    atok = asttokens.ASTTokens(source, parse=True)

    # Locate the first FunctionDef node in the AST.
    function_node = None
    for node in ast.walk(atok.tree):  # type: ignore[arg-type]
        if isinstance(node, ast.FunctionDef):
            function_node = node
            break
    if function_node is None:
        msg = "Function definition not found in source."
        raise ValueError(msg)

    # Extract the source for each statement in the function body.
    start = atok.get_text_range(function_node.body[0], padded=False)[0]
    end = atok.get_text_range(function_node.body[-1], padded=False)[1]
    body = dedent(_guess_indentation(source) + source[start:end])
    if not body.endswith("\n"):
        body += "\n"
    return body
