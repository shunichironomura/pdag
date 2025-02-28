import ast
from collections.abc import Mapping
from typing import Any

from ._core import CoreModel, FunctionRelationship, ParameterABC, RelationshipABC, SubModelRelationship


def _parameter_nodes_to_ast_statements(nodes: Mapping[str, ParameterABC[Any]]) -> list[ast.stmt]:
    return [
        ast.AnnAssign(
            target=ast.Name(id=name, ctx=ast.Store()),
            annotation=ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id="pdag", ctx=ast.Load()),
                    attr=parameter.__class__.__name__,
                    ctx=ast.Load(),
                ),
                args=[ast.Constant(value=name)],
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
                        attr=parameter.__class__.__name__,
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


def _make_function_body_ast(function_body: str) -> ast.stmt:
    return ast.parse(function_body).body[0]


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
    relationship: FunctionRelationship,
    *,
    core_model: CoreModel,
) -> ast.FunctionDef:
    return ast.FunctionDef(
        name=relationship.name,
        args=ast.arguments(
            kwonlyargs=[
                _make_arg_ast(arg_name, core_model.nodes[parameter_name])
                for arg_name, parameter_name in relationship.inputs.items()
            ],
            kw_defaults=[None for _ in relationship.inputs],
        ),
        body=[
            _make_function_body_ast(relationship.function_body),
        ],
        decorator_list=[
            ast.Attribute(
                value=ast.Name(id="pdag", ctx=ast.Load()),
                attr="relationship",
                ctx=ast.Load(),
            ),
            ast.Name(id="staticmethod", ctx=ast.Load()),
        ],
        returns=_make_return_ast(
            [core_model.nodes[parameter_name] for parameter_name in relationship.outputs],
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
    parameters = _parameter_nodes_to_ast_statements(core_model.nodes)
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
