from collections.abc import Callable

from pdag._core import FunctionRelationship

from .model import function_to_function_relationship


def relationship[**P, T](func: Callable[P, T]) -> FunctionRelationship[P, T]:
    """Decorate a function to mark it as a relationship."""
    return function_to_function_relationship(func)
