"""Example models for building expansion."""

from dataclasses import dataclass
from typing import ClassVar

import pdag


class NpvCalculationModel(pdag.Model):
    """A model for calculating the net present value of a project."""

    @dataclass
    class Settings:
        """Settings that are specific to the model instances."""

        n_time_steps: int


class BuildingExpansionModel(pdag.Model):
    """A model for building expansion."""

    class Constants:
        """Constants that are shared across all model instances."""

        building_states: ClassVar[tuple[str, ...]] = ("none", "opt-33", "opt-57", "exp-33", "exp-57")
        actions: ClassVar[tuple[str, ...]] = (
            "none",
            "build-opt-33",
            "build-opt-57",
            "teardown-opt-33-and-build-opt-57",
            "build-exp-33",
            "exp-to-57",
        )
        policy_types: ClassVar[tuple[str, ...]] = (
            "none",
            "build-opt-57",
            "build-opt-33-and-rebuild",
            "build-exp-33-and-expand",
        )

    @dataclass
    class Settings:
        """Settings that are specific to the model instances."""

        n_time_steps: int = 4
        revenue_per_floor: float = 3
