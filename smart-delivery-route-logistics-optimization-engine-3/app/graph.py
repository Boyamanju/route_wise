"""Small weighted graph and Dijkstra implementation used by the delivery API."""

from __future__ import annotations

from dataclasses import dataclass
import heapq
from math import inf
from typing import Literal


class GraphError(ValueError):
    """Raised when a graph operation would create an invalid road network."""


class RouteNotFoundError(LookupError):
    """Raised when two valid intersections have no usable route between them."""


@dataclass(frozen=True)
class RouteResult:
    path: list[str]
    total_cost: float
    traversal: list[str]


TrafficAction = Literal["slow_down", "block", "restore"]


class Graph:
    """A weighted graph stored as an adjacency list.

    `base_adjacency` preserves original road distances so traffic conditions can
    be restored. `adjacency` is the current routable road network. Removing a
    road from `adjacency` represents a temporary block.
    """

    def __init__(self, *, directed: bool = False) -> None:
        self.directed = directed
        self.adjacency: dict[str, dict[str, float]] = {}
        self.base_adjacency: dict[str, dict[str, float]] = {}

    def add_node(self, node: str) -> None:
        """Add an intersection if it does not already exist."""
        self.adjacency.setdefault(node, {})
        self.base_adjacency.setdefault(node, {})

    def add_edge(self, source: str, destination: str, weight: float) -> None:
        """Add or replace a road. Dijkstra requires a non-negative weight."""
        self._validate_weight(weight)
        self.add_node(source)
        self.add_node(destination)
        normalized_weight = float(weight)
        self.adjacency[source][destination] = normalized_weight
        self.base_adjacency[source][destination] = normalized_weight
        if not self.directed:
            self.adjacency[destination][source] = normalized_weight
            self.base_adjacency[destination][source] = normalized_weight

    def apply_traffic(
        self,
        source: str,
        destination: str,
        action: TrafficAction,
        multiplier: float | None = None,
    ) -> float | None:
        """Change one road condition and return its current weight, or None if blocked."""
        self._require_base_road(source, destination)

        if action == "block":
            self._remove_current_road(source, destination)
            return None

        if action == "restore":
            updated_weight = self.base_adjacency[source][destination]
        elif action == "slow_down":
            if multiplier is None or multiplier < 1:
                raise GraphError("multiplier must be at least 1 for slow_down")
            updated_weight = self.base_adjacency[source][destination] * multiplier
        else:  # Defensive guard for callers outside the FastAPI schema.
            raise GraphError(f"unsupported traffic action: {action}")

        self.adjacency[source][destination] = updated_weight
        if not self.directed:
            self.adjacency[destination][source] = updated_weight
        return updated_weight

    def shortest_path(self, source: str, destination: str) -> RouteResult:
        """Find a shortest route using Dijkstra's algorithm and a min-heap."""
        self._require_node(source)
        self._require_node(destination)

        distances = {node: inf for node in self.adjacency}
        previous: dict[str, str] = {}
        distances[source] = 0.0
        candidates: list[tuple[float, str]] = [(0.0, source)]
        settled: set[str] = set()
        traversal: list[str] = []

        while candidates:
            current_distance, current_node = heapq.heappop(candidates)
            if current_node in settled:
                continue  # Ignore an older, more expensive heap entry.

            settled.add(current_node)
            traversal.append(current_node)
            if current_node == destination:
                break  # Its shortest distance is now guaranteed.

            for neighbor, road_cost in self.adjacency[current_node].items():
                if neighbor in settled:
                    continue
                new_distance = current_distance + road_cost
                if new_distance < distances[neighbor]:
                    distances[neighbor] = new_distance
                    previous[neighbor] = current_node
                    heapq.heappush(candidates, (new_distance, neighbor))

        if distances[destination] == inf:
            raise RouteNotFoundError(f"No usable route from '{source}' to '{destination}'.")

        path = self._reconstruct_path(previous, source, destination)
        return RouteResult(path=path, total_cost=distances[destination], traversal=traversal)

    def roads(self) -> list[dict[str, float | str | None]]:
        """Return one record per road, including blocked roads, for API display."""
        result: list[dict[str, float | str | None]] = []
        seen: set[tuple[str, str]] = set()
        for source, neighbors in self.base_adjacency.items():
            for destination, base_weight in neighbors.items():
                road_id = tuple(sorted((source, destination))) if not self.directed else (source, destination)
                if road_id in seen:
                    continue
                seen.add(road_id)
                result.append(
                    {
                        "from_node": source,
                        "to_node": destination,
                        "base_weight": base_weight,
                        "current_weight": self.adjacency[source].get(destination),
                    }
                )
        return result

    def _remove_current_road(self, source: str, destination: str) -> None:
        self.adjacency[source].pop(destination, None)
        if not self.directed:
            self.adjacency[destination].pop(source, None)

    def _require_base_road(self, source: str, destination: str) -> None:
        self._require_node(source)
        self._require_node(destination)
        if destination not in self.base_adjacency[source]:
            raise GraphError(f"No road exists between '{source}' and '{destination}'.")

    def _require_node(self, node: str) -> None:
        if node not in self.adjacency:
            raise GraphError(f"Unknown intersection: '{node}'.")

    @staticmethod
    def _validate_weight(weight: float) -> None:
        if weight < 0:
            raise GraphError("Negative road weights are not supported by Dijkstra's algorithm.")

    @staticmethod
    def _reconstruct_path(previous: dict[str, str], source: str, destination: str) -> list[str]:
        path = [destination]
        while path[-1] != source:
            path.append(previous[path[-1]])
        return list(reversed(path))


def validate_with_networkx(graph: Graph, source: str, destination: str) -> bool:
    """Compare the custom result with NetworkX; useful as an independent test oracle."""
    import networkx as nx

    nx_graph = nx.DiGraph() if graph.directed else nx.Graph()
    for node, neighbors in graph.adjacency.items():
        nx_graph.add_node(node)
        for neighbor, weight in neighbors.items():
            nx_graph.add_edge(node, neighbor, weight=weight)

    custom = graph.shortest_path(source, destination)
    expected_cost = nx.shortest_path_length(nx_graph, source, destination, weight="weight")
    return custom.total_cost == expected_cost
