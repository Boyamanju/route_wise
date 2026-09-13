"""FastAPI entry point for the delivery routing demo."""

from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

from app.graph import Graph, GraphError, RouteNotFoundError


app = FastAPI(
    title="Smart Delivery Route Engine",
    version="1.0.0",
    description="A small delivery-routing API powered by a custom Dijkstra implementation.",
)
app.mount("/assets", StaticFiles(directory="app/static"), name="assets")


def build_sample_city() -> Graph:
    """A deliberately small city map that makes traffic rerouting easy to see."""
    city = Graph()
    for source, destination, distance in [
        ("Yeshwanthpur Hub", "Majestic", 4),
        ("Majestic", "Indiranagar", 4),
        ("Yeshwanthpur Hub", "Ulsoor Lake", 6),
        ("Ulsoor Lake", "Indiranagar", 5),
        ("Majestic", "M. G. Road", 2),
        # Kept slightly longer than the Ulsoor option so traffic demos
        # produce one clear rerouted path instead of a tied result.
        ("M. G. Road", "Indiranagar", 6),
    ]:
        city.add_edge(source, destination, distance)
    return city


city_graph = build_sample_city()


class RouteResponse(BaseModel):
    path: list[str]
    total_cost: float
    traversal: list[str] = Field(description="Nodes settled by Dijkstra, in order.")


class TrafficRequest(BaseModel):
    from_node: str
    to_node: str
    action: Literal["slow_down", "block", "restore"]
    multiplier: float | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_action_parameters(self) -> "TrafficRequest":
        if self.action == "slow_down" and self.multiplier is None:
            raise ValueError("multiplier is required when action is slow_down")
        return self


class TrafficResponse(BaseModel):
    message: str
    from_node: str
    to_node: str
    current_weight: float | None


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    """Serve the friendly dashboard; API documentation remains available at /docs."""
    return FileResponse("app/static/index.html")


@app.get("/instructions", include_in_schema=False)
def instructions() -> FileResponse:
    """Serve a short, practical guide for the dashboard."""
    return FileResponse("app/static/instructions.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/route", response_model=RouteResponse)
def route(
    source: str = Query(..., min_length=1),
    destination: str = Query(..., min_length=1),
) -> RouteResponse:
    """Calculate the currently cheapest usable delivery route."""
    try:
        result = city_graph.shortest_path(source, destination)
        return RouteResponse(**result.__dict__)
    except RouteNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except GraphError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/simulate-traffic", response_model=TrafficResponse)
def simulate_traffic(request: TrafficRequest) -> TrafficResponse:
    """Apply a traffic condition to one road; it remains active until restored."""
    try:
        current_weight = city_graph.apply_traffic(
            request.from_node,
            request.to_node,
            request.action,
            multiplier=request.multiplier,
        )
        return TrafficResponse(
            message=f"Applied '{request.action}' to {request.from_node} -> {request.to_node}.",
            from_node=request.from_node,
            to_node=request.to_node,
            current_weight=current_weight,
        )
    except GraphError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/reset-traffic")
def reset_traffic() -> dict[str, str]:
    """Restore every road to the initial demo condition."""
    global city_graph
    city_graph = build_sample_city()
    return {"message": "All road conditions have been restored."}


@app.get("/network")
def network() -> dict[str, list[dict[str, float | str | None]] | list[str]]:
    """Inspect the current city map, including blocked and altered roads."""
    return {"intersections": sorted(city_graph.adjacency), "roads": city_graph.roads()}
