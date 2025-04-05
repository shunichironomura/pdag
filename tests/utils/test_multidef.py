from typing import ClassVar

from pdag._utils import MultiDef, multidef


class C(MultiDef):
    a: ClassVar[list[int]] = [1, 2]

    def f(self) -> list[int]:
        return self.a

    # In a loop, define multiple versions of 'g'.
    for i in range(3):

        @multidef(i)
        @staticmethod
        def g(i: int = i) -> int:
            return i


def test_multidef_access() -> None:
    c = C()

    assert c.get_def("g", 0)() == 0
    assert c.g[0]() == 0
    assert c.get_def("g", 0)(i=1) == 1
    assert c.g[0](i=1) == 1
    assert c.get_def("g", 1)() == 1
    assert c.g[1]() == 1
    assert c.get_def("g", 2)() == 2  # noqa: PLR2004
    assert c.g[2]() == 2  # noqa: PLR2004
    assert c.a == [1, 2]
