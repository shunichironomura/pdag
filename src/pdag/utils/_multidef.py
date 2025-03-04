from abc import ABCMeta
from collections.abc import Callable
from typing import Any, cast


# A custom dict that collects duplicate definitions in the class body.
class MultiDict[K, V](dict[K, V | list[V]]):
    def __setitem__(self, key: K, value: V | list[V]) -> None:
        # We know that value is of type V
        # But the method signature of the parent class requires it to be of type V | list[V]
        value = cast(V, value)

        if key in self:
            existing = super().__getitem__(key)
            # Only aggregate if the new value have our decorator marker.
            # We don't check for the existing value because it may already be a list.
            if hasattr(value, "__multidef_identifier__"):
                if isinstance(existing, list):
                    assert all(hasattr(item, "__multidef_identifier__") for item in existing)
                    existing.append(value)
                else:
                    super().__setitem__(key, [existing, value])
            else:
                # For any other values (e.g. loop variables like i), simply override.
                super().__setitem__(key, value)
        else:
            super().__setitem__(key, value)


def _to_unique_name(attr: str, identifier: Any) -> str:
    return f"{attr}__{identifier}"


# The decorator simply attaches an identifier to the function.
def multidef(identifier: Any) -> Callable[..., Any]:
    _unique_name = _to_unique_name("_", identifier)
    assert _unique_name.isidentifier(), f"Invalid identifier: {identifier!r}. Attribute name could be {_unique_name!r}."

    def decorator[T](obj: T) -> T:
        try:
            obj.__multidef_identifier__ = identifier  # type: ignore[attr-defined]
        except AttributeError as e:
            msg = "multidef can only be used on objects that support attribute assignment."
            raise TypeError(msg) from e

        return obj

    return decorator


class MultiDefMeta(ABCMeta):
    @classmethod
    def __prepare__(metacls, name: str, bases: tuple[type[Any], ...], /, **kwargs: Any) -> MultiDict[str, Any]:  # noqa: N804
        return MultiDict()

    def __new__(metacls, name: str, bases: tuple[type[Any], ...], namespace: dict[str, Any]) -> type:  # noqa: N804
        # Create the class first using a normal dict
        cls = super().__new__(metacls, name, bases, dict(namespace))
        # Now process duplicate definitions in the original namespace.
        for attr, value in namespace.items():
            if isinstance(value, list) and all(hasattr(obj, "__multidef_identifier__") for obj in value):
                for obj in value:
                    # Only process objects that have our marker
                    if hasattr(obj, "__multidef_identifier__"):
                        unique_name = _to_unique_name(attr, obj.__multidef_identifier__)
                        setattr(cls, unique_name, obj)
                # Optionally, assign the last defined function to the original name.
                setattr(cls, attr, value[-1])
        return cls


# Example class using the metaclass and the decorator.
class MultiDef(metaclass=MultiDefMeta):
    def get_name(self, attr: str, identifier: Any) -> str:
        return _to_unique_name(attr, identifier)

    def get_def(self, attr: str, identifier: Any) -> Any:
        return getattr(self, self.get_name(attr, identifier))
