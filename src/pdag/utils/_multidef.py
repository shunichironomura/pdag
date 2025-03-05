from abc import ABCMeta
from collections.abc import Callable, Hashable, Iterable
from typing import Any, Protocol

type IdentifierType = Hashable


class MultiDefStorage[T](dict[IdentifierType, T]):
    pass


# A custom dict that collects duplicate definitions in the class body.
class MultiDict[K, V](dict[K, V | MultiDefStorage[V]]):
    def __setitem__(self, key: K, value: V | MultiDefStorage[V]) -> None:
        if isinstance(value, MultiDefStorage):
            msg = "Cannot assign a MultiDefStorage directly to a MultiDict."
            raise TypeError(msg)

        if hasattr(value, "__multidef_identifier__"):
            identifier: IdentifierType = value.__multidef_identifier__
            if key in self:
                existing = super().__getitem__(key)
                # Only aggregate if the new value have our decorator marker.
                # We don't check for the existing value because it may already be a list.
                if isinstance(existing, MultiDefStorage):
                    assert all(hasattr(item, "__multidef_identifier__") for item in existing.values())
                    existing[identifier] = value
                else:
                    msg = f"Existing value for {key!r} is not a multidef object, cannot aggregate."
                    raise ValueError(msg)
            else:
                # First time we see this key, create a new MultiDefStorage
                super().__setitem__(key, MultiDefStorage({identifier: value}))

        else:
            super().__setitem__(key, value)


def _to_unique_name(attr: str, identifier_str: str) -> str:
    return f"__multidef_{attr}_{identifier_str}__"


def _to_identifier_str(identifier: IdentifierType) -> str:
    """Try to convert the identifier to a string that can be used as an attribute name."""
    if isinstance(identifier, str):
        return identifier
    if isinstance(identifier, Iterable):
        return "_".join(map(_to_identifier_str, identifier))

    # Fallback to the default string representation.
    # If this cannot be used as an attribute name, the user will get an error.
    return str(identifier)


class MultiDefProtocol[K: IdentifierType, T](Protocol):
    def __getitem__(self, identifier: K) -> T: ...


# The decorator simply attaches an identifier to the function.
# The type hints are not correct here, but will be corrected by the metaclass.
def multidef[K: IdentifierType, T](
    identifier: K,
) -> Callable[[T], MultiDefProtocol[K, T]]:
    _unique_name = _to_unique_name("_", _to_identifier_str(identifier))
    if not _unique_name.isidentifier():
        msg = f"Invalid identifier: {identifier!r}. Attribute name could be {_unique_name!r}."
        raise ValueError(msg)

    def decorator[_K: IdentifierType, _T](
        obj: _T,
    ) -> MultiDefProtocol[_K, _T]:
        try:
            obj.__multidef_identifier__ = identifier  # type: ignore[attr-defined]
        except AttributeError as e:
            msg = "multidef can only be used on objects that support attribute assignment."
            raise TypeError(msg) from e

        return obj  # type: ignore[return-value]

    return decorator


class MultiDefMeta(ABCMeta):
    @classmethod
    def __prepare__(
        metacls,  # noqa: N804
        name: str,
        bases: tuple[type[Any], ...],
        /,
        **kwargs: Any,
    ) -> MultiDict[str, Any]:
        return MultiDict()

    def __new__(
        metacls,  # noqa: N804
        name: str,
        bases: tuple[type[Any], ...],
        namespace: dict[str, Any],
    ) -> type:
        # Create the class first using a normal dict
        cls = super().__new__(metacls, name, bases, dict(namespace))
        # Now process duplicate definitions in the original namespace.
        for attr, value in namespace.items():
            if isinstance(value, MultiDefStorage):
                identifier_to_unique_name = {
                    identifier: _to_unique_name(attr, _to_identifier_str(identifier)) for identifier in value
                }
                for identifier, obj in value.items():
                    # Only process objects that have our marker
                    unique_name = identifier_to_unique_name[identifier]
                    setattr(cls, unique_name, obj)

        return cls


# Example class using the metaclass and the decorator.
class MultiDef(metaclass=MultiDefMeta):
    def get_name(self, attr: str, identifier: IdentifierType) -> str:
        return _to_unique_name(attr, _to_identifier_str(identifier))

    def get_def(self, attr: str, identifier: IdentifierType) -> Any:
        return getattr(self, self.get_name(attr, identifier))

    def get_defs(self, attr: str) -> dict[IdentifierType, Any]:
        return {identifier: self.get_def(attr, identifier) for identifier in super().__getattribute__(attr)}

    def __getattribute__(self, name: str) -> Any:
        value = super().__getattribute__(name)
        if isinstance(value, MultiDefStorage):
            return self.get_defs(name)
        return value
