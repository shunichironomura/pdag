import ast
import inspect
from collections.abc import Callable
from textwrap import dedent
from typing import Any

import asttokens


def get_function_body(func: Callable[..., Any]) -> str:
    """Get the body of a function as a string."""
    source = inspect.getsource(func)
    source = dedent(source)
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
    start = atok.get_text_range(function_node.body[0], padded=True)[0]
    end = atok.get_text_range(function_node.body[-1], padded=True)[1]
    body = dedent(source[start:end])
    if not body.endswith("\n"):
        body += "\n"
    return body
