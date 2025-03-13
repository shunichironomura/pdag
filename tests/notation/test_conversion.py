import pytest

import pdag

from .cases import CASES_DC_NOTATION_TO_CORE_MODEL


@pytest.mark.parametrize(("dc_notation", "core_model"), CASES_DC_NOTATION_TO_CORE_MODEL)
def test_dataclass_notation_to_core_model(
    dc_notation: type[pdag.Model],
    core_model: pdag.CoreModel,
) -> None:
    # Compare CoreModel
    exported_core_model = dc_notation.to_core_model()
    assert exported_core_model == core_model
