"""Examples module that contains example models.

!!! warning
    The examples are not intended to be used in production code and are provided for demonstration purposes only.
"""

__all__ = [
    "DiamondMdpModel",
    "EachSquaredModel",
    "PolynomialModel",
    "SquareModel",
    "TwoSquares",
    "UmbrellaModel",
]
from ._diamond_mdp import DiamondMdpModel
from ._each_squared import EachSquaredModel
from ._polynomials import PolynomialModel
from ._square import SquareModel
from ._squares import TwoSquares
from ._umbrella import UmbrellaModel
