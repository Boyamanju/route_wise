const state = { roads: [], intersections: [] };

const $ = (selector) => document.querySelector(selector);
const source = $("#source");
const destination = $("#destination");
const trafficRoad = $("#traffic-road");
const routeResult = $("#route-result");
const emptyResult = $("#empty-result");
const bangalorePlaces = {
  "Yeshwanthpur Hub": { coordinates: [13.0284, 77.5425] },
  Majestic: { coordinates: [12.9767, 77.5713] },
  Indiranagar: { coordinates: [12.9784, 77.6408] },
  "Ulsoor Lake": { coordinates: [12.9814, 77.6208] },
  "M. G. Road": { coordinates: [12.9756, 77.6067] },
};
let cityMap;
let mapRoute;
let mapMarkers = [];
let routeRenderer;

function initialiseMap() {
  if (!window.L) {
    $("#map-status").textContent = "Map tiles unavailable";
    return;
  }
  cityMap = L.map("bangalore-map", {
    zoomControl: false,
    attributionControl: true,
    scrollWheelZoom: false,
    zoomSnap: 0.5,
  }).setView([12.989, 77.595], 12);
  routeRenderer = L.canvas({ padding: 0.5 });
  L.control.zoom({ position: "bottomleft" }).addTo(cityMap);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "© OpenStreetMap contributors",
  }).addTo(cityMap);
  // Leaflet may initialise before the animated hero has its final dimensions.
  // Recalculate whenever its card changes size so its tiles stay in their box.
  const mapElement = $("#bangalore-map");
  let resizeFrame;
  new ResizeObserver(() => {
    cancelAnimationFrame(resizeFrame);
    resizeFrame = requestAnimationFrame(() => cityMap.invalidateSize({ pan: false, animate: false }));
  }).observe(mapElement);
  window.addEventListener("load", () => cityMap.invalidateSize({ pan: false, animate: false }), { once: true });
  window.setTimeout(() => cityMap.invalidateSize({ pan: false, animate: false }), 800);
}

function markerIcon(kind, number) {
  return L.divIcon({
    className: "",
    html: `<div class="map-marker ${kind}"><b>${number}</b></div>`,
    iconSize: [27, 27],
    iconAnchor: [14, 27],
  });
}

async function drawMapRoute(stops) {
  if (!cityMap || !stops.every((stop) => bangalorePlaces[stop])) return;
  mapMarkers.forEach((marker) => marker.remove());
  mapMarkers = stops.map((stop, index) => {
    const kind = index === 0 ? "start" : index === stops.length - 1 ? "end" : "middle";
    return L.marker(bangalorePlaces[stop].coordinates, { icon: markerIcon(kind, index + 1) })
      .addTo(cityMap)
      .bindTooltip(`${index + 1}. ${stop}`, { direction: "top" });
  });
  if (mapRoute) mapRoute.remove();
  const coordinates = stops.map((stop) => bangalorePlaces[stop].coordinates);
  mapRoute = L.polyline(coordinates, {
    renderer: routeRenderer,
    color: "#a8ef70",
    weight: 7,
    opacity: 1,
    dashArray: "10 10",
    lineCap: "round",
    lineJoin: "round",
  }).addTo(cityMap);
  mapRoute.bringToFront();
  cityMap.invalidateSize();
  cityMap.fitBounds(mapRoute.getBounds(), { padding: [45, 45], maxZoom: 13 });
  $("#map-status").textContent = "Finding road-by-road route…";
  try {
    const osrmPoints = coordinates.map(([lat, lng]) => `${lng},${lat}`).join(";");
    const response = await fetch(`https://router.project-osrm.org/route/v1/driving/${osrmPoints}?overview=full&geometries=geojson`);
    const data = await response.json();
    if (!response.ok || !data.routes?.[0]) throw new Error("Road route unavailable");
    mapRoute.remove();
    mapRoute = L.polyline(data.routes[0].geometry.coordinates.map(([lng, lat]) => [lat, lng]), {
      renderer: routeRenderer,
      color: "#a8ef70",
      weight: 7,
      opacity: 1,
      lineCap: "round",
      lineJoin: "round",
    }).addTo(cityMap);
    mapRoute.bringToFront();
    cityMap.fitBounds(mapRoute.getBounds(), { padding: [45, 45], maxZoom: 13 });
    $("#map-status").textContent = `${stops.length} real stops · road route ready`;
  } catch (_) {
    $("#map-status").textContent = "Route preview · road service retrying";
  }
}

function toast(message) {
  const element = $("#toast");
  element.textContent = message;
  element.classList.add("show");
  window.clearTimeout(toast.timer);
  toast.timer = window.setTimeout(() => element.classList.remove("show"), 3200);
}

function labelForRoad(road) {
  const condition = road.current_weight === null ? " · closed" : " · open";
  return `${road.from_node} ↔ ${road.to_node}${condition}`;
}

function populateSelect(select, values, selectedValue) {
  select.innerHTML = values.map((value) => `<option value="${value}">${value}</option>`).join("");
  if (selectedValue && values.includes(selectedValue)) select.value = selectedValue;
}

async function loadNetwork() {
  const response = await fetch("/network");
  if (!response.ok) throw new Error("Could not load the city network.");
  const network = await response.json();
  state.intersections = network.intersections;
  state.roads = network.roads;
  populateSelect(source, state.intersections, source.value || "Yeshwanthpur Hub");
  populateSelect(destination, state.intersections, destination.value || "Indiranagar");
  trafficRoad.innerHTML = state.roads.map((road, index) => `<option value="${index}">${labelForRoad(road)}</option>`).join("");
  $("#intersection-count").textContent = state.intersections.length;
  $("#road-count").textContent = state.roads.length;
}

function showRoute(route) {
  $("#total-cost").textContent = `${route.total_cost} points`;
  $("#route-stops").innerHTML = route.path.map((stop) => `<span class="stop">${stop}</span>`).join("");
  $("#traversal-copy").textContent = `The planner compared these locations while finding the lowest-cost path: ${route.traversal.join(" → ")}.`;
  emptyResult.classList.add("hidden");
  routeResult.classList.remove("hidden");
  $("#route-state").innerHTML = "<i></i> Route ready";
  drawMapRoute(route.path);
}

async function findRoute(event) {
  event?.preventDefault();
  if (source.value === destination.value) {
    toast("Pick two different locations to plan a route.");
    return;
  }
  $("#route-state").textContent = "Finding route…";
  try {
    const query = new URLSearchParams({ source: source.value, destination: destination.value });
    const response = await fetch(`/route?${query}`);
    const route = await response.json();
    if (!response.ok) throw new Error(route.detail || "No route found.");
    showRoute(route);
    toast("Best route found — ready to deliver.");
  } catch (error) {
    $("#route-state").textContent = "Needs attention";
    toast(error.message);
  }
}

function updateTrafficFields() {
  const action = $("#traffic-action").value;
  $("#multiplier-field").classList.toggle("hidden", action !== "slow_down");
}

async function applyTraffic(event) {
  event.preventDefault();
  const road = state.roads[Number(trafficRoad.value)];
  const action = $("#traffic-action").value;
  const payload = { from_node: road.from_node, to_node: road.to_node, action };
  if (action === "slow_down") payload.multiplier = Number($("#multiplier").value);
  const message = $("#traffic-message");
  message.className = "traffic-message";
  message.textContent = "Updating road conditions…";
  try {
    const response = await fetch("/simulate-traffic", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Could not update this road.");
    const friendlyWeight = data.current_weight === null ? "The road is now closed." : "The traffic condition is active.";
    message.textContent = `${friendlyWeight} Search again to see the new route.`;
    message.classList.add("success");
    await loadNetwork();
    toast("Traffic update applied.");
  } catch (error) {
    message.textContent = error.message;
    message.classList.add("error");
  }
}

async function resetRoads() {
  const message = $("#traffic-message");
  try {
    const response = await fetch("/reset-traffic", { method: "POST" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Could not reset road conditions.");
    message.className = "traffic-message success";
    message.textContent = data.message;
    await loadNetwork();
    await findRoute();
    toast("Road conditions reset.");
  } catch (error) {
    message.className = "traffic-message error";
    message.textContent = error.message;
  }
}

$("#route-form").addEventListener("submit", findRoute);
$("#traffic-form").addEventListener("submit", applyTraffic);
$("#traffic-action").addEventListener("change", updateTrafficFields);
$("#swap-points").addEventListener("click", () => { [source.value, destination.value] = [destination.value, source.value]; });
$("#reset-roads").addEventListener("click", resetRoads);
initialiseMap();
loadNetwork().then(() => findRoute()).catch((error) => toast(error.message));
