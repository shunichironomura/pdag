"""Utility functions and classes for the pdag package."""

import ast
import inspect
from collections import defaultdict, deque
from collections.abc import Callable, Collection, Hashable, Mapping
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
        # This is a bit of a hack to avoid assigning to attributes
        # even if the inherited dataclass has frozen=True
        object.__setattr__(instance, "__init_args__", args)
        object.__setattr__(instance, "__init_kwargs__", kwargs)
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


def topological_sort[T: Hashable](dependencies: Mapping[T, Collection[T]]) -> list[T]:
    """Sort a graph of dependencies topologically.

    Given a dependency graph (a dict mapping a node to a collection of nodes that depend on it),
    perform a topological sort and return an ordered list of nodes.
    Raises an error if a cycle is detected.
    """
    indegree: defaultdict[T, int] = defaultdict(int)
    for node, deps in dependencies.items():
        indegree[node] = indegree.get(node, 0)
        for dep in deps:
            indegree[dep] += 1
    q = deque([node for node, deg in indegree.items() if deg == 0])
    order = []
    while q:
        node = q.popleft()
        order.append(node)
        for dep in dependencies.get(node, []):
            indegree[dep] -= 1
            if indegree[dep] == 0:
                q.append(dep)
    if len(order) != len(indegree):
        msg = "Cycle detected in relationship dependencies!"
        raise ValueError(msg)
    return order


def merge_two_set_dicts[K, V](d1: Mapping[K, set[V]], d2: Mapping[K, set[V]]) -> dict[K, set[V]]:
    """Merge two dictionaries where each value is a set.

    Values for duplicate keys are merged (unioned).
    """
    result = dict(d1)
    for key, value in d2.items():
        result[key] = result.get(key, set()) | value
    return result
