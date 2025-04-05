from pdag.utils import merge_two_set_dicts


def test_merge_two_set_dicts() -> None:
    d1 = {"a": {1, 2}, "b": {3}}
    d2 = {"b": {4}, "c": {5, 6}}
    merged = merge_two_set_dicts(d1, d2)
    assert merged == {"a": {1, 2}, "b": {3, 4}, "c": {5, 6}}
