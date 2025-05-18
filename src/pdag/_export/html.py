import importlib.resources
from collections import defaultdict
from pathlib import Path
from typing import Any

from jinja2 import BaseLoader, Environment, Template

from pdag._core.model import CoreModel
from pdag._exec.to_exec_model import _iter_submodels_recursively

from .dot import to_dot_graph, tuple_to_html_id


def template_factory() -> Template:
    template_text = importlib.resources.files("pdag._export").joinpath("assets/graph.j2").read_text(encoding="utf-8")

    env = Environment(loader=BaseLoader(), autoescape=True)
    return env.from_string(template_text)


def _model_path_to_model_id(model_path: tuple[str, ...]) -> str:
    return tuple_to_html_id(model_path) if model_path else "__root__"


def _model_id_to_model_container_id(model_id: str) -> str:
    return f"model-container-{model_id}"


def export_html(core_model: CoreModel, path: Path) -> None:
    graph_data: dict[str, Any] = {}
    click_events_dd: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)

    for model_path, submodel in _iter_submodels_recursively(core_model, include_self=True):
        model_id = _model_path_to_model_id(model_path)
        graph = to_dot_graph(submodel, model_element_id=model_id)
        svg_data: bytes = graph.create_svg()  # pyright: ignore[reportAttributeAccessIssue]
        svg_string = svg_data.decode("utf-8")
        model_container_id = _model_id_to_model_container_id(model_id)

        if model_path:
            parent_model_path = model_path[:-1]
            parent_model_id = _model_path_to_model_id(parent_model_path)
            parent_node_id = tuple_to_html_id((parent_model_id, model_path[-1]))
            parent_model_container_id = _model_id_to_model_container_id(parent_model_id)
            assert parent_model_container_id in graph_data
            click_events_dd[parent_model_container_id].append(
                {
                    "source_id": parent_node_id,
                    "target_graph_id": model_container_id,
                },
            )

        assert model_container_id not in graph_data
        graph_data[model_container_id] = {
            "id": model_container_id,
            "svg": svg_string,
        }

    click_events: dict[str, list[dict[str, Any]]] = dict(click_events_dd)

    template = template_factory()
    rendered_html = template.render(
        title=core_model.name,
        graphs=[{"id": k, "click_events": click_events.get(k, []), **v} for k, v in graph_data.items()],
    )

    with path.open("w", encoding="utf-8") as f:
        f.write(rendered_html)
