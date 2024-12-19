from pathlib import Path

from pdag._server._model import ReactFlowGraph


def test_parse_react_flow_graph(datadir: Path) -> None:
    react_flow_graph_json = (datadir / "react_flow_graph.json").read_text()
    ReactFlowGraph.model_validate_json(react_flow_graph_json)


def test_dump_parsed_react_flow_graph(datadir: Path) -> None:
    react_flow_graph_json = (datadir / "react_flow_graph.json").read_text()
    graph = ReactFlowGraph.model_validate_json(react_flow_graph_json)
    # Ignore the trailing newline differences
    assert graph.model_dump_json(indent=4, by_alias=True, round_trip=True).rstrip() == react_flow_graph_json.rstrip()
