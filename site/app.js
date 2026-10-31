/* Desert Hours map. All figures come from data/*.json, built by pipeline/build_data.py. */
const DESTS = ["Capital Health Regional Medical Center", "Trenton Transit Center", "Hamilton Marketplace"];
const MAP_REGION = "us-east-1";
const $ = (id) => document.getElementById(id);
const hourName = (h) => {
  const x = h % 24, s = x < 12 ? "AM" : "PM", n = x % 12 || 12;
  return x === 12 ? "Noon" : x === 0 ? "Midnight" : `${n} ${s}`;
};
const fmt = (n) => Number(n).toLocaleString("en-US");
const dur = (m) => (m < 60 ? `${m} min` : `${Math.floor(m / 60)}h ${String(m % 60).padStart(2, "0")}m`);
let state = { hour: 8, tract: null, summary: null, timer: null };

const style = window.MAP_KEY
  ? `https://maps.geo.${MAP_REGION}.amazonaws.com/v2/styles/Monochrome/descriptor?key=${window.MAP_KEY}&color-scheme=Dark`
  : { version: 8, sources: {}, layers: [{ id: "bg", type: "background", paint: { "background-color": "#0c1014" } }] };

const map = new maplibregl.Map({ container: "map", style, center: [-74.68, 40.27], zoom: 10, attributionControl: { compact: true } });
map.addControl(new maplibregl.NavigationControl({ showCompass: false }));

function outExpr(h) {
  return ["-", 1, ["at", h % 24, ["get", "cov"]]];
}

function paint() {
  const h = state.hour % 24;
  if (map.getLayer("tracts")) {
    map.setPaintProperty("tracts", "fill-color", ["interpolate", ["linear"], outExpr(h), 0, "#3a3226", 0.5, "#a56a1f", 1, "#f0a13a"]);
    map.setFilter("reach", ["==", ["get", "h"], h]);
  }
  $("hourlabel").textContent = hourName(state.hour);
  if (state.summary) $("bignum").textContent = fmt(state.summary.out[h]);
  drawChart();
  if (state.tract) showTract(state.tract);
}

function drawChart() {
  const s = state.summary;
  if (!s) return;
  const order = [...Array(24).keys()].map((i) => (i + 5) % 24);
  const w = 800, ht = 56, max = s.zero;
  const pts = order.map((h, i) => [(i / 23) * w, ht - 4 - (s.out[h] / max) * (ht - 10)]);
  const line = pts.map((p) => p.map((v) => v.toFixed(1)).join(",")).join(" ");
  const cur = pts[state.hour - 5];
  $("chart").innerHTML = `<svg viewBox="0 0 ${w} ${ht}" preserveAspectRatio="none"><polyline points="${line}" fill="none" stroke="#f0a13a" stroke-width="2" vector-effect="non-scaling-stroke"/><line x1="${cur[0]}" x2="${cur[0]}" y1="0" y2="${ht}" stroke="#eef2f5" stroke-width="1" vector-effect="non-scaling-stroke"/></svg>`;
}

function tripCell(t, h) {
  if (!t) return "No route";
  if (t.min > 600) return "Next day";
  return dur(t.min);
}

function showTract(p) {
  const h = state.hour % 24;
  const cov = p.cov, dep = p.dep;
  const mx = Math.max(...dep, 1);
  const order = [...Array(24).keys()].map((i) => (i + 5) % 24);
  const bars = order.map((x) => `<i class="${x === h ? "on" : ""}" style="height:${Math.round((dep[x] / mx) * 100)}%" title="${hourName(x)}: ${dep[x]} departures"></i>`).join("");
  const rows = DESTS.map((d) => {
    const t = (p.trips || {})[d];
    if (!t) return "";
    const car = t.car && t.car.min !== undefined ? `${t.car.min} min` : "—";
    const c = (k) => { const v = t[k]; return v && v.min !== undefined ? tripCell(v) : "No route"; };
    return `<tr class="dest"><td colspan="5">${d}</td></tr><tr><td>${c("8")}</td><td>${c("17")}</td><td>${c("23")}</td><td>${c("2")}</td><td>${car}</td></tr>`;
  }).join("");
  const two = ((p.trips || {})[DESTS[0]] || {})["2"];
  $("panel").innerHTML = `<h2>${p.name}</h2><p class="sub">${p.muni}</p>
  <div class="stats">
    <div class="stat"><b>${fmt(p.zero)}</b><span>car-free households (±${fmt(p.moe)}), of ${fmt(p.hh)}</span></div>
    <div class="stat"><b>${Math.round(cov[h] * 100)}%</b><span>of housing within a 10-minute walk at ${hourName(state.hour)}</span></div>
  </div>
  <h3>Departures within a 10-minute walk of any part of the tract</h3>
  <div class="bars">${bars}</div><div class="axis"><span>5 AM</span><span>Noon</span><span>Midnight</span><span>4 AM</span></div>
  <h3>Leave at, by transit, against driving</h3>
  <table class="trip"><thead><tr><th>8 AM</th><th>5 PM</th><th>11 PM</th><th>2 AM</th><th>Car</th></tr></thead><tbody>${rows}</tbody></table>
  ${two && two.leave ? `<p class="note">Leaving for the hospital at 2 AM, you set out at ${two.leave} and arrive at ${two.arrive}.</p>` : ""}
  ${p.local ? `<p class="note">Route 130 Connection stops are nearby.</p>` : ""}`;
}

function setHour(v) {
  state.hour = Number(v);
  $("hour").value = state.hour;
  paint();
}

function toggle() {
  if (state.timer) {
    clearInterval(state.timer);
    state.timer = null;
    $("play").textContent = "▶";
    return;
  }
  $("play").textContent = "❚❚";
  state.timer = setInterval(() => setHour(state.hour >= 28 ? 5 : state.hour + 1), 700);
}

$("hour").addEventListener("input", (e) => setHour(e.target.value));
$("play").addEventListener("click", toggle);

map.on("load", async () => {
  const [tracts, summary] = await Promise.all([fetch("data/tracts.geojson").then((r) => r.json()), fetch("data/summary.json").then((r) => r.json())]);
  state.summary = summary;
  const firstLabel = map.getStyle().layers.find((l) => l.type === "symbol");
  const before = firstLabel ? firstLabel.id : undefined;
  map.addSource("tracts", { type: "geojson", data: tracts });
  map.addLayer({ id: "tracts", type: "fill", source: "tracts", paint: { "fill-opacity": 0.72 } }, before);
  map.addSource("reach", { type: "geojson", data: "data/reach.geojson" });
  map.addLayer({ id: "reach", type: "fill", source: "reach", paint: { "fill-color": "#4fb3d9", "fill-opacity": 0.65 } }, before);
  map.addLayer({ id: "lines", type: "line", source: "tracts", paint: { "line-color": "#101418", "line-width": 0.7 } }, before);
  map.addLayer({ id: "pick", type: "line", source: "tracts", paint: { "line-color": "#ffffff", "line-width": 2.5 }, filter: ["==", ["get", "g"], ""] });
  const b = new maplibregl.LngLatBounds();
  tracts.features.forEach((f) => (f.geometry.coordinates.flat(Infinity).length ? f.geometry.coordinates.flat(f.geometry.type === "Polygon" ? 1 : 2).forEach((c) => b.extend(c)) : 0));
  map.fitBounds(b, { padding: 20, duration: 0 });
  const select = (p) => {
    state.tract = p;
    map.setFilter("pick", ["==", ["get", "g"], p.g]);
    showTract(p);
  };
  const byId = Object.fromEntries(tracts.features.map((f) => [f.properties.g, f.properties]));
  map.on("click", "tracts", (e) => select(byId[e.features[0].properties.g]));
  map.on("mouseenter", "tracts", () => (map.getCanvas().style.cursor = "pointer"));
  map.on("mouseleave", "tracts", () => (map.getCanvas().style.cursor = ""));
  $("story").addEventListener("click", () => {
    select(byId["34021000100"]);
    setHour(23);
    map.flyTo({ center: [-74.755, 40.195], zoom: 12.8 });
  });
  paint();
});
