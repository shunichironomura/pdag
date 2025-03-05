from collections.abc import Callable, Mapping

type ElementOrArrayType[T] = list["ElementOrArrayType[T]"] | T


def nested_map[T1, T2](f: Callable[[T1], T2], data: ElementOrArrayType[T1]) -> ElementOrArrayType[T2]:
    if isinstance(data, list):
        return [nested_map(f, item) for item in data]
    return f(data)


def nested_list_from_mapping[T](  # noqa: D417
    mapping: Mapping[tuple[int, ...], T],
    shape: tuple[int, ...],
    *,
    default_value: T | None = None,
    error_on_missing: bool = False,
) -> ElementOrArrayType[T]:
    """Create a nested list of given shape from a mapping.

    Parameters
    ----------
    - mapping: dict, where keys are tuples of indices (e.g., (2, 3)) and values are the desired values.
    - shape: tuple of ints defining the shape of the nested list.
    - default_value: value to use if an index tuple is missing from the mapping.

    Returns
    -------
    - A nested list with the specified shape.

    """

    def helper(indices: tuple[int, ...], shape: tuple[int, ...]) -> ElementOrArrayType[T]:
        if not shape:  # No more dimensions; return the value for the current index tuple.
            if error_on_missing:
                return mapping[indices]
            return mapping.get(indices, default_value)  # type: ignore[arg-type]
        return [helper((*indices, i), shape[1:]) for i in range(shape[0])]

    return helper((), shape)
