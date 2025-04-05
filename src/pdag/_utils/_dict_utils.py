from collections.abc import Mapping


def merge_two_set_dicts[K, V](d1: Mapping[K, set[V]], d2: Mapping[K, set[V]]) -> dict[K, set[V]]:
    """Merge two dictionaries where each value is a set.

    Values for duplicate keys are merged (unioned).

    Example:
    ```python
    d1 = {"a": {1, 2}, "b": {3}}
    d2 = {"b": {4}, "c": {5, 6}}
    merged = merge_two_set_dicts(d1, d2)
    # merged is {"a": {1, 2}, "b": {3, 4}, "c": {5, 6}}
    ```

    """
    result = dict(d1)
    for key, value in d2.items():
        result[key] = result.get(key, set()) | value
    return result
