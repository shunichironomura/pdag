from typing import Annotated

import pdag


def test_capture_plain_parameter() -> None:
    class Model(pdag.Model):
        x = pdag.RealParameter("x")

    assert Model.parameters() == {"x": pdag.RealParameter("x")}


def test_time_step_parameter() -> None:
    class Model(pdag.Model):
        x = pdag.RealParameter("x", is_time_series=True)

    assert Model.parameters() == {"x": pdag.RealParameter("x", is_time_series=True)}


def test_capture_plain_relationship() -> None:
    class Model(pdag.Model):
        x = pdag.RealParameter("x")
        y = pdag.RealParameter("y")

        @pdag.relationship
        @staticmethod
        def f(x_arg: Annotated[float, pdag.ParameterRef("x")]) -> Annotated[float, pdag.ParameterRef("y")]:
            return x_arg

    assert Model.relationships() == {
        "f": pdag.FunctionRelationship(
            name="f",
            inputs={"x_arg": pdag.ParameterRef("x")},
            outputs=[pdag.ParameterRef("y")],
            output_is_scalar=True,
            function_body="return x_arg\n",
            _function=Model.f._function,  # noqa: SLF001
            at_each_time_step=False,
        ),
    }
