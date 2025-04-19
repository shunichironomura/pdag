from typing import Annotated

import pdag


class EachSquaredModel(pdag.Model):
    """EachSquaredModel model that uses a mapping of parameters."""

    m = pdag.Mapping("m", {k: pdag.RealParameter(...) for k in ("a", "b", "c")})
    m_squared = pdag.Mapping("m_squared", {k: pdag.RealParameter(...) for k in ("a", "b", "c")})

    for k in ("a", "b", "c"):
        # You need to provide the identifier to distinguish each relationship
        @pdag.relationship(identifier=k)
        @staticmethod
        def square(
            # The annotation `m.ref(k)` indicates that the value of `m[k]` will be provided
            # when the model is executed.
            m_arg: Annotated[float, m.ref(k)],
            # The annotation `m_squared.ref(k)` indicates that the return value of the method
            # will be assigned to `m_squared[k]` when the model is executed.
        ) -> Annotated[float, m_squared.ref(k)]:
            return m_arg**2
