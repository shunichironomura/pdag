"""Utility functions and classes for the pdag package."""

import ast
import inspect
from collections.abc import Callable
from textwrap import dedent
from typing import Any, Self

import asttokens


class InitArgsRecorder:
    """A mixin class that records the arguments used to initialize the instance."""

    # These are not class variables, but instance variables
    # They are declared here to inform type checkers.
    __init_args__: tuple[Any, ...]
    __init_kwargs__: dict[str, Any]

    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        """Record the arguments used to initialize the instance."""
        # Create the instance first
        instance = super().__new__(cls)
        # Save the arguments for later inspection
        instance.__init_args__ = args
        instance.__init_kwargs__ = kwargs
        return instance

    def get_init_args(self) -> tuple[Any, ...]:
        """Return the arguments used to initialize the instance."""
        return self.__init_args__

    def get_init_kwargs(self) -> dict[str, Any]:
        """Return the keyword arguments used to initialize the instance."""
        return self.__init_kwargs__


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
