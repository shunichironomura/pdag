from textwrap import dedent
from typing import Annotated, Literal

import pdag


class SquareRootModel(pdag.Model):
    x = pdag.RealParameter("x")
    y = pdag.RealParameter("y")
    z = pdag.CategoricalParameter("z", categories=("pos", "neg"))

    @pdag.relationship
    @staticmethod
    def sqrt(
        *,
        x_arg: Annotated[float, pdag.ParameterRef("x")],
        z_arg: Annotated[Literal["pos", "neg"], pdag.ParameterRef("z")],
    ) -> Annotated[float, pdag.ParameterRef("y")]:
        if z_arg == "pos":
            return float(x_arg**0.5)
        return -float(x_arg**0.5)


square_root_core_model = pdag.CoreModel(
    name="SquareRootModel",
    parameters={
        "x": pdag.RealParameter("x"),
        "y": pdag.RealParameter("y"),
        "z": pdag.CategoricalParameter("z", categories=("pos", "neg")),
    },
    collections={},
    relationships={
        "sqrt": pdag.FunctionRelationship(
            name="sqrt",
            inputs={"x_arg": pdag.ParameterRef("x"), "z_arg": pdag.ParameterRef("z")},
            outputs=[pdag.ParameterRef("y")],
            output_is_scalar=True,
            function_body=dedent(
                """\
                if z_arg == "pos":
                    return float(x_arg**0.5)
                return -float(x_arg**0.5)
                """,
            ),
            at_each_time_step=False,
        ),
    },
)

_TECHNOLOGIES = ["tech1", "tech2", "tech3"]


class TechDevCompletionModel(pdag.Model):
    dev_start_time = pdag.Mapping(
        "dev_start_time",
        {tech: pdag.RealParameter(...) for tech in _TECHNOLOGIES},
    )
    dev_time = pdag.Mapping(
        "dev_time",
        {tech: pdag.RealParameter(...) for tech in _TECHNOLOGIES},
    )
    dev_completion_time = pdag.Mapping(
        "dev_completion_time",
        {tech: pdag.RealParameter(...) for tech in _TECHNOLOGIES},
    )

    for tech in _TECHNOLOGIES:

        @pdag.relationship(identifier=tech)
        @staticmethod
        def dev_completion_time_model(
            dev_start_time: Annotated[float, pdag.MappingRef("dev_start_time", tech)],
            dev_time: Annotated[float, pdag.MappingRef("dev_time", tech)],
        ) -> Annotated[float, pdag.MappingRef("dev_completion_time", tech)]:
            return dev_start_time + dev_time


tech_dev_completion_core_model = pdag.CoreModel(
    name="TechDevCompletionModel",
    parameters={f"dev_start_time[{tech}]": pdag.RealParameter(f"dev_start_time[{tech}]") for tech in _TECHNOLOGIES}  # type: ignore[arg-type]
    | {f"dev_time[{tech}]": pdag.RealParameter(f"dev_time[{tech}]") for tech in _TECHNOLOGIES}
    | {f"dev_completion_time[{tech}]": pdag.RealParameter(f"dev_completion_time[{tech}]") for tech in _TECHNOLOGIES},
    collections={
        "dev_start_time": pdag.Mapping(
            "dev_start_time",
            {tech: pdag.RealParameter(f"dev_start_time[{tech}]") for tech in _TECHNOLOGIES},
        ),
        "dev_time": pdag.Mapping(
            "dev_time",
            {tech: pdag.RealParameter(f"dev_time[{tech}]") for tech in _TECHNOLOGIES},
        ),
        "dev_completion_time": pdag.Mapping(
            "dev_completion_time",
            {tech: pdag.RealParameter(f"dev_completion_time[{tech}]") for tech in _TECHNOLOGIES},
        ),
    },
    relationships={
        "dev_completion_time_model": pdag.FunctionRelationship(
            name="dev_completion_time_model",
            inputs={
                "dev_start_time": pdag.MappingRef("dev_start_time"),
                "dev_time": pdag.MappingRef("dev_time"),
            },
            outputs=[pdag.MappingRef("dev_completion_time")],
            output_is_scalar=True,
            function_body=dedent(
                """\
                return dev_start_time + dev_time
                """,
            ),
            at_each_time_step=False,
        ),
    },
)

CASES_DC_NOTATION_TO_CORE_MODEL = [
    (SquareRootModel, square_root_core_model),
]
CASES_CORE_MODEL_TO_DC_NOTATION = [
    (SquareRootModel, square_root_core_model),
]
