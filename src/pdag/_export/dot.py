from collections.abc import Hashable
from pathlib import Path
from typing import Any

import pydot

from pdag._core import CollectionABC, CoreModel, ExecInfo
from pdag._core.collection import key_to_str
from pdag._core.parameter import ParameterABC
from pdag._core.relationship import RelationshipABC


def _mapping_node(
    collection: CollectionABC[Hashable, ParameterABC[Any] | RelationshipABC],
) -> pydot.Node:
    peripheries = 1
    if collection.item_type == "parameter" and collection.is_time_series():
        peripheries = 2
    if collection.item_type == "relationship":
        first_relationship = next(iter(collection.values()))
        assert isinstance(first_relationship, RelationshipABC)
        if first_relationship.at_each_time_step:
            peripheries = 2

    header_row = "<TR><TD BGCOLOR='lightgrey'>"
    header_row += f"<B>{collection.name}</B></TD></TR>"

    def _item_to_row(key: Hashable) -> str:
        key_label = key_to_str(key, make_one_element_tuple_scalar=True)
        return f"<TR><TD PORT='{key_label}'>{key_label}</TD></TR>"

    rows = header_row + "".join(_item_to_row(key) for key in collection.keys())  # noqa: SIM118
    table = f'<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">{rows}</TABLE>'
    label = f"<{table}>"

    return pydot.Node(
        collection.name,
        shape="oval" if collection.item_type == "parameter" else "box",
        peripheries=peripheries,
        label=label,
    )


def export_dot(core_model: CoreModel, path: Path) -> None:  # noqa: C901, PLR0912
    graph = pydot.Dot(core_model.name, graph_type="digraph")
    added_exec_infos: set[str] = set()

    for name, parameter in core_model.parameters.items():
        if parameter.is_time_series:
            graph.add_node(pydot.Node(name, shape="oval", peripheries=2))
        else:
            graph.add_node(pydot.Node(name, shape="oval"))

    for name, relationship in core_model.relationships.items():
        if relationship.at_each_time_step:
            graph.add_node(pydot.Node(name, shape="box", peripheries=2))
        else:
            graph.add_node(pydot.Node(name, shape="box"))

        for input_ref in relationship.iter_input_refs():
            if isinstance(input_ref, ExecInfo):
                if input_ref.attribute not in added_exec_infos:
                    graph.add_node(pydot.Node(input_ref.attribute, shape="diamond"))
                    added_exec_infos.add(input_ref.attribute)
                graph.add_edge(pydot.Edge(input_ref.attribute, name))
            else:
                style = "dashed" if input_ref.previous else "solid"
                graph.add_edge(pydot.Edge(input_ref.name, name, style=style))

        for output_ref in relationship.iter_output_refs():
            style = "dashed" if output_ref.next else "solid"
            graph.add_edge(pydot.Edge(name, output_ref.name, style=style))

    for name, collection in core_model.collections.items():
        graph.add_node(_mapping_node(collection))
        key, first_item = next(iter(collection.items()))
        if isinstance(first_item, RelationshipABC):
            for input_ref in first_item.iter_input_refs():
                if isinstance(input_ref, ExecInfo):
                    if input_ref.attribute not in added_exec_infos:
                        graph.add_node(pydot.Node(input_ref.attribute, shape="diamond"))
                        added_exec_infos.add(input_ref.attribute)
                    graph.add_edge(pydot.Edge(input_ref.attribute, name))
                else:
                    style = "dashed" if input_ref.previous else "solid"
                    graph.add_edge(pydot.Edge(input_ref.name, name, style=style))

            for output_ref in first_item.iter_output_refs():
                style = "dashed" if output_ref.next else "solid"
                graph.add_edge(pydot.Edge(name, output_ref.name, style=style))

    graph.write(path, format="png")
