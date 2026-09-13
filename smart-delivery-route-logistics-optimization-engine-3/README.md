# Smart Delivery Route & Logistics Optimization Engine

A FastAPI project that finds a low-cost delivery route through a small Bengaluru-inspired road network. It uses a custom adjacency-list graph and a from-scratch Dijkstra implementation with a min-heap. NetworkX is used only in tests to validate results.

The project is deliberately compact: every important decision is visible in a few files, rather than hidden behind a routing framework.

## What it demonstrates

- Modeling intersections and roads as a weighted graph
- Dijkstra's shortest-path algorithm using `heapq`
- Dynamic road conditions: slow a road, block it, or restore it
- A typed FastAPI surface with useful error responses
- Tests for cycles, disconnection, invalid negative weights, traffic rerouting, and NetworkX cross-validation

## Quick start

Requires Python 3.11+.

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` to use the interactive API documentation.

## Try it

The service starts with a small Bengaluru-inspired sample city. `Yeshwanthpur Hub` to `Indiranagar` initially goes through `Majestic`.

```bash
curl "http://127.0.0.1:8000/route?source=Yeshwanthpur%20Hub&destination=Indiranagar"
```

Slow the normally preferred road, then ask for the route again:

```bash
curl -X POST "http://127.0.0.1:8000/simulate-traffic" \
  -H "Content-Type: application/json" \
  -d '{"from_node":"Majestic","to_node":"Indiranagar","action":"slow_down","multiplier":3}'
```

```bash
curl "http://127.0.0.1:8000/route?source=Yeshwanthpur%20Hub&destination=Indiranagar"
```

Restore the original road weight with `action: "restore"`, or make a road unusable with `action: "block"`.

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /route?source=...&destination=...` | Returns the best path, total distance, and the nodes permanently settled by Dijkstra. |
| `POST /simulate-traffic` | Blocks, slows, or restores one road. |
| `POST /reset-traffic` | Restores all roads to the initial sample network. |
| `GET /network` | Shows the current city map and current road conditions. |
| `GET /health` | Lightweight service status check. |

## How the algorithm works

The graph stores `node -> {neighbor: distance}`. Dijkstra keeps a min-heap of candidate `(total_distance, node)` entries.

1. Start the source with distance `0`.
2. Pop the closest unvisited node from the heap.
3. Relax every outgoing road: if going through this node improves a neighbor's known distance, update the distance and push it to the heap.
4. Stop when the destination is settled, then reconstruct the route through `previous` pointers.

With an adjacency list and heap, the runtime is **O((V + E) log V)** (commonly stated as **O(E log V)** for connected road networks) and space is **O(V + E)**. A linear scan for the next closest node would make the selection step O(V), yielding O(V^2) overall.

## Design notes for an interview

**Why a custom graph instead of only NetworkX?** The project is meant to show command of the data structure and shortest-path mechanics. NetworkX is kept as an independent oracle in tests, not as the production routing implementation.

**Why reject negative weights?** Dijkstra assumes that once the nearest node is settled, no later path can improve it. A negative road violates that assumption. Use Bellman-Ford when negative edges are meaningful (and to detect negative cycles).

**How would it scale?** Keep the API stateless and place graph/traffic state in a shared store. For large maps, partition by geography, precompute contraction hierarchies, and use A* with an admissible geographic heuristic for point-to-point queries. Real systems also version live traffic updates rather than mutating a single in-memory graph.

## Run tests

```bash
pytest
```

## Put it online

Yes. This project includes a `Dockerfile` and `render.yaml`, so it is ready to deploy as a public website after you push it to GitHub.

1. Create a new empty GitHub repository (for example, `routewise-delivery-planner`).
2. In this project folder, run:

```powershell
git init
git add .
git commit -m "Initial Routewise delivery planner"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/routewise-delivery-planner.git
git push -u origin main
```

3. Sign in to [Render](https://render.com), select **New + → Blueprint**, and select the GitHub repository.
4. Render reads `render.yaml`, builds the Docker image, and gives you a public `https://...onrender.com` address.

The interactive Bengaluru map uses OpenStreetMap map tiles and the public OSRM routing service, so it needs internet access when the deployed website is open.

## Project layout

```text
app/
  graph.py     # graph, traffic updates, Dijkstra, NetworkX validation helper
  main.py      # FastAPI routes and request/response models
tests/         # algorithm and API tests
```
