"""pdag: A package for defining and working with directed acyclic graphs (DAGs) of parameters and relationships."""

__all__ = [
    "CategoricalParameter",
    "CoreModel",
    "FunctionRelationship",
    "Model",
    "ParameterABC",
    "ParameterArray",
    "ParameterCollectionABC",
    "ParameterMapping",
    "ParameterRef",
    "RealParameter",
    "RelationshipABC",
    "SubModelRelationship",
    "core_model_to_content",
    "core_model_to_dataclass_notation_ast",
    "module_to_content",
    "relationship",
    "utils",
]


from . import utils  # expose utils module
from ._core import (
    CategoricalParameter,
    CoreModel,
    FunctionRelationship,
    ParameterABC,
    ParameterArray,
    ParameterCollectionABC,
    ParameterMapping,
    RealParameter,
    RelationshipABC,
    SubModelRelationship,
)
from ._decorators import relationship
from ._notation import (
    Model,
    ParameterRef,
    core_model_to_content,
    core_model_to_dataclass_notation_ast,
    module_to_content,
)
