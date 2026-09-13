from fastapi.testclient import TestClient

from app.main import app, build_sample_city
import app.main as main


def setup_function() -> None:
    # Reset global demo state so traffic changes do not leak between tests.
    main.city_graph = build_sample_city()


def test_route_endpoint_returns_path_distance_and_traversal() -> None:
    response = TestClient(app).get(
        "/route", params={"source": "Yeshwanthpur Hub", "destination": "Indiranagar"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "path": ["Yeshwanthpur Hub", "Majestic", "Indiranagar"],
        "total_cost": 8.0,
        "traversal": ["Yeshwanthpur Hub", "Majestic", "M. G. Road", "Ulsoor Lake", "Indiranagar"],
    }


def test_dashboard_is_available() -> None:
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert "Delivery route planner" in response.text


def test_instructions_page_is_available() -> None:
    response = TestClient(app).get("/instructions")

    assert response.status_code == 200
    assert "How to use" in response.text


def test_reset_traffic_restores_the_demo_network() -> None:
    client = TestClient(app)
    client.post(
        "/simulate-traffic",
        json={"from_node": "Majestic", "to_node": "Indiranagar", "action": "block"},
    )

    response = client.post("/reset-traffic")
    route = client.get("/route", params={"source": "Yeshwanthpur Hub", "destination": "Indiranagar"})

    assert response.status_code == 200
    assert route.json()["path"] == ["Yeshwanthpur Hub", "Majestic", "Indiranagar"]


def test_traffic_endpoint_reroutes_delivery() -> None:
    client = TestClient(app)
    update = client.post(
        "/simulate-traffic",
        json={
            "from_node": "Majestic",
            "to_node": "Indiranagar",
            "action": "slow_down",
            "multiplier": 3,
        },
    )
    route = client.get("/route", params={"source": "Yeshwanthpur Hub", "destination": "Indiranagar"})

    assert update.status_code == 200
    assert update.json()["current_weight"] == 12.0
    assert route.json()["path"] == ["Yeshwanthpur Hub", "Ulsoor Lake", "Indiranagar"]
    assert route.json()["total_cost"] == 11.0
