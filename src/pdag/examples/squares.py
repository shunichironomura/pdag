"""Squares example to demonstrate mapping containing submodels."""

from typing import Annotated

import pdag

from .square import SquareModel


class TwoSquares(pdag.Model):
    """TwoSquares model.

    Calculates z = x^2 + y^2
    """

    x = pdag.RealParameter("x")
    x_squared = pdag.RealParameter("x_squared")
    y = pdag.RealParameter("y")
    y_squared = pdag.RealParameter("y_squared")
    z = pdag.RealParameter("z")

    calc_square_term = pdag.Mapping(
        "calc_square_term",
        {
            input_param.name: SquareModel.to_relationship(
                ...,
                inputs={SquareModel.x.ref(): input_param.ref()},
                outputs={SquareModel.y.ref(): output_param.ref()},
            )
            for (input_param, output_param) in [(x, x_squared), (y, y_squared)]
        },
    )

    @pdag.relationship
    @staticmethod
    def squares(  # noqa: D102
        *,
        x_squared: Annotated[float, x_squared.ref()],
        y_squared: Annotated[float, y_squared.ref()],
    ) -> Annotated[float, z.ref()]:
        return x_squared + y_squared


if __name__ == "__main__":
    from rich import print  # noqa: A004

    core_model = TwoSquares.to_core_model()
    print(core_model)
    exec_model = pdag.create_exec_model_from_core_model(core_model)
    print(exec_model)
