import pytest

from app.graph import Graph, GraphError, RouteNotFoundError, validate_with_networkx


def test_dijkstra_chooses_shortest_path_in_a_cyclic_graph() -> None:
    graph = Graph()
    graph.add_edge("A", "B", 2)
    graph.add_edge("B", "C", 2)
    graph.add_edge("C", "A", 10)  # Creates a cycle, but is not optimal.
    graph.add_edge("C", "D", 1)

    result = graph.shortest_path("A", "D")

    assert result.path == ["A", "B", "C", "D"]
    assert result.total_cost == 5
    assert validate_with_networkx(graph, "A", "D")


def test_disconnected_graph_has_no_route() -> None:
    graph = Graph()
    graph.add_edge("A", "B", 1)
    graph.add_node("C")

    with pytest.raises(RouteNotFoundError, match="No usable route"):
        graph.shortest_path("A", "C")


def test_negative_weights_are_rejected() -> None:
    graph = Graph()

    with pytest.raises(GraphError, match="Negative"):
        graph.add_edge("A", "B", -1)


def test_blocking_road_changes_route_and_restore_recovers_it() -> None:
    graph = Graph()
    graph.add_edge("A", "B", 1)
    graph.add_edge("B", "C", 1)
    graph.add_edge("A", "C", 5)

    assert graph.shortest_path("A", "C").path == ["A", "B", "C"]
    assert graph.apply_traffic("B", "C", "block") is None
    assert graph.shortest_path("A", "C").path == ["A", "C"]
    assert graph.apply_traffic("B", "C", "restore") == 1
    assert graph.shortest_path("A", "C").path == ["A", "B", "C"]
