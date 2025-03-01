import ast
from collections.abc import Mapping
from typing import Any

from pdag._core import CoreModel, FunctionRelationship, Module, ParameterABC, RelationshipABC, SubModelRelationship


def _object_to_ast_value(obj: Any) -> ast.expr:
    """Convert an object to an AST value.

    This relies on the `repr` of the object being a valid Python expression.
    """
    return ast.parse(repr(obj)).body[0].value  # type: ignore[no-any-return,attr-defined]


def _parameter_nodes_to_ast_statements(nodes: Mapping[str, ParameterABC[Any]]) -> list[ast.stmt]:
    return [
        ast.AnnAssign(
            target=ast.Name(id=name, ctx=ast.Store()),
            annotation=ast.Subscript(
                value=ast.Name(id="Annotated", ctx=ast.Load()),
                slice=ast.Tuple(
                    elts=[
                        _type_hint_to_ast_node(parameter.get_type_hint()),
                        ast.Call(
                            func=ast.Attribute(
                                value=ast.Name(id="pdag", ctx=ast.Load()),
                                attr=parameter.__class__.__name__,
                                ctx=ast.Load(),
                            ),
                            args=[_object_to_ast_value(arg) for arg in parameter.get_init_args()],
                            keywords=[
                                ast.keyword(arg=key, value=_object_to_ast_value(value))
                                for key, value in parameter.get_init_kwargs().items()
                            ],
                        ),
                    ],
                ),
            ),
            simple=1,
        )
        for name, parameter in nodes.items()
    ]


def _type_hint_to_ast_node(type_hint: str) -> ast.expr:
    return ast.parse(type_hint).body[0].value  # type: ignore[no-any-return,attr-defined]


def _make_annotated_type_hint(parameter: ParameterABC[Any]) -> ast.Subscript:
    return ast.Subscript(
        value=ast.Name(id="Annotated", ctx=ast.Load()),
        slice=ast.Tuple(
            elts=[
                _type_hint_to_ast_node(parameter.get_type_hint()),
                ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id="pdag", ctx=ast.Load()),
                        attr="Parameter",
                        ctx=ast.Load(),
                    ),
                    args=[ast.Constant(value=parameter.name)],
                ),
            ],
            ctx=ast.Load(),
        ),
        ctx=ast.Load(),
    )


def _make_arg_ast(arg_name: str, parameter: ParameterABC[Any]) -> ast.arg:
    return ast.arg(
        arg=arg_name,
        annotation=_make_annotated_type_hint(parameter),
    )


def _make_function_body_ast(function_body: str) -> list[ast.stmt]:
    return ast.parse(function_body).body


def _make_return_ast(parameters: list[ParameterABC[Any]], *, force_tuple: bool = False) -> ast.Subscript:
    if len(parameters) == 1 and not force_tuple:
        return _make_annotated_type_hint(parameters[0])
    return ast.Subscript(
        value=ast.Name(id="tuple", ctx=ast.Load()),
        slice=ast.Tuple(
            elts=[_make_annotated_type_hint(parameter) for parameter in parameters],
            ctx=ast.Load(),
        ),
    )


def _function_relationship_to_function_def(
    relationship: FunctionRelationship[Any, Any],
    *,
    core_model: CoreModel,
) -> ast.FunctionDef:
    return ast.FunctionDef(
        name=relationship.name,
        args=ast.arguments(
            kwonlyargs=[
                _make_arg_ast(arg_name, core_model.parameters[parameter_ref.name])
                for arg_name, parameter_ref in relationship.inputs.items()
            ],
            kw_defaults=[None for _ in relationship.inputs],
        ),
        body=_make_function_body_ast(relationship.function_body),
        decorator_list=[
            ast.Attribute(
                value=ast.Name(id="pdag", ctx=ast.Load()),
                attr="relationship",
                ctx=ast.Load(),
            ),
            ast.Name(id="staticmethod", ctx=ast.Load()),
        ],
        returns=_make_return_ast(
            [core_model.parameters[parameter_ref.name] for parameter_ref in relationship.outputs],
        ),
    )


def _submodel_relationship_to_function_def(
    relationship: SubModelRelationship,
    *,
    core_model: CoreModel,
) -> ast.FunctionDef:
    raise NotImplementedError


def _relationship_to_function_def(
    relationship: RelationshipABC,
    *,
    core_model: CoreModel,
) -> ast.FunctionDef:
    if isinstance(relationship, FunctionRelationship):
        return _function_relationship_to_function_def(relationship, core_model=core_model)
    if isinstance(relationship, SubModelRelationship):
        return _submodel_relationship_to_function_def(relationship, core_model=core_model)
    msg = f"Unknown relationship type: {type(relationship)}"
    raise ValueError(msg)


def core_model_to_dataclass_notation_ast(core_model: CoreModel) -> ast.ClassDef:
    parameters = _parameter_nodes_to_ast_statements(core_model.parameters)
    relationships: list[ast.stmt] = [
        _relationship_to_function_def(relationship, core_model=core_model)
        for relationship in core_model.relationships.values()
    ]
    return ast.ClassDef(
        name=core_model.name,
        bases=[
            ast.Attribute(
                value=ast.Name(id="pdag", ctx=ast.Load()),
                attr="Model",
                ctx=ast.Load(),
            ),
        ],
        keywords=[],
        body=parameters + relationships,
    )


def core_model_to_content(core_model: CoreModel) -> str:
    module = ast.Module(body=[core_model_to_dataclass_notation_ast(core_model)], type_ignores=[])
    module = ast.fix_missing_locations(module)
    return ast.unparse(module)


def module_to_content(module: Module) -> str:
    return module.pre_models + "\n\n".join(core_model_to_content(model) for model in module.models) + module.post_models
