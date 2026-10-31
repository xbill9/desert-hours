#!/usr/bin/env python3
"""Build Desert Hours data: hourly walkable transit coverage by census tract, Mercer County NJ.

Households are placed on 2020 Census blocks by housing units, assuming car-free households
are spread like housing within a tract.

Every number shown on the site comes from this script. Inputs live in data/raw (see README).
Reach defaults to a 400 m circle round each stop; data/isolines/<stop>.json, when present,
replaces the circle with an Amazon Location Pedestrian isoline.
"""
import collections, csv, datetime, json, math, pathlib, sys, warnings
import shapefile
from shapely import make_valid
from shapely.geometry import Point, mapping, shape
from shapely.ops import transform, unary_union

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw"
ISO = ROOT / "data/isolines"
OUT = ROOT / "site/data"
RADIUS_M = 400.0
# Route 130 Connection weekday timetable effective 2023-09-11 (GMTMA PDF): hours (24h) with a
# departure at Rogers Ave & Mercer St in either direction. Stops come from the county layer.
RT130_HOURS = {2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19}
LAT0, LON0 = 40.27, -74.70
KX, KY = 111320 * math.cos(math.radians(LAT0)), 110540


def to_m(x, y, z=None):
    return ((x - LON0) * KX, (y - LAT0) * KY)


def to_ll(x, y, z=None):
    return (x / KX + LON0, y / KY + LAT0)


def read_shapes(name):
    r = shapefile.Reader(str(RAW / "geo" / name), encoding="utf-8")
    return [s for s in r.iterShapeRecords() if s.record["COUNTYFP"] == "021"]


tract_ll, tract_m = {}, {}
for s in read_shapes("tl_2023_34_tract.shp"):
    g = make_valid(shape(s.shape.__geo_interface__))
    tract_ll[s.record["GEOID"]] = g
    tract_m[s.record["GEOID"]] = transform(to_m, g)
muni_m = {s.record["NAMELSAD"]: transform(to_m, make_valid(shape(s.shape.__geo_interface__)))
          for s in read_shapes("tl_2023_34_cousub.shp")}
muni = {g: max(muni_m, key=lambda n: muni_m[n].intersection(p).area) for g, p in tract_m.items()}
county = unary_union(list(tract_m.values()))
near = county.buffer(1500)

acs = json.load(open(RAW / "cr.json"))
vintage = acs.get("release", {}).get("name", "unknown")
hh, zero, zero_moe = {}, {}, {}
for k, v in acs["data"].items():
    g = k[7:]
    t = v["B08201"]
    hh[g], zero[g], zero_moe[g] = t["estimate"]["B08201001"], t["estimate"]["B08201002"], t["error"]["B08201002"]

stops = {}  # key -> dict(xy, dep[24])
meta = {}
for mode in ("bus", "rail"):
    d = RAW / mode
    cd = list(csv.DictReader(open(d / "calendar_dates.txt")))
    cnt = collections.Counter(x["date"] for x in cd if x["exception_type"] == "1")
    day = max((x for x in cnt if datetime.date(int(x[:4]), int(x[4:6]), int(x[6:])).weekday() == 2),
              key=lambda x: (cnt[x], x))
    svc = {x["service_id"] for x in cd if x["date"] == day and x["exception_type"] == "1"}
    trips = {x["trip_id"] for x in csv.DictReader(open(d / "trips.txt")) if x["service_id"] in svc}
    local = {}
    for x in csv.DictReader(open(d / "stops.txt")):
        p = Point(to_m(float(x["stop_lon"]), float(x["stop_lat"])))
        if near.contains(p):
            local[x["stop_id"]] = f"{mode}-{x['stop_id']}"
            stops[local[x["stop_id"]]] = {"xy": (p.x, p.y), "dep": [0] * 24, "local": False,
                                           "ll": (float(x["stop_lon"]), float(x["stop_lat"]))}
    for x in csv.DictReader(open(d / "stop_times.txt")):
        if x["trip_id"] in trips and x["stop_id"] in local:
            h = int(x["departure_time"].split(":")[0]) % 24
            stops[local[x["stop_id"]]]["dep"][h] += 1
    meta[mode] = {"day": day, "dates": [min(cnt), max(cnt)], "trips": len(trips)}

for f in json.load(open(RAW / "layer1.geojson"))["features"]:
    lon, lat = f["geometry"]["coordinates"][:2]
    x, y = to_m(lon, lat)
    stops[f"rt130-{f['properties']['OBJECTID']}"] = {"xy": (x, y), "dep": [0] * 24, "local": True, "ll": (lon, lat)}


json.dump({k: s["ll"] for k, s in stops.items()}, open(ROOT / "data/stops.json", "w"))


def reach(key, s):
    f = ISO / f"{key}.json"
    if f.exists():
        return transform(to_m, shape(json.load(open(f))))
    return Point(s["xy"]).buffer(RADIUS_M, 12)


if "--stops-only" in sys.argv:
    sys.exit()
zones = {k: make_valid(reach(k, s)) for k, s in stops.items()}
iso_used = sum((ISO / f"{k}.json").exists() for k in stops)
hours = list(range(24))
cover = {}
for h in hours:
    act = [k for k, s in stops.items() if s["dep"][h] > 0 or (s["local"] and h in RT130_HOURS)]
    cover[h] = unary_union([zones[k] for k in act]).intersection(county) if act else None

# Place each tract's households on its 2020 Census blocks by housing-unit count.
from shapely import STRtree
blocks = collections.defaultdict(list)
for s in shapefile.Reader(str(RAW / "geo/tl_2020_34_tabblock20.shp"), encoding="utf-8").iterShapeRecords():
    if s.record["COUNTYFP20"] != "021" or not s.record["HOUSING20"]:
        continue
    blocks[s.record["GEOID20"][:11]].append((Point(to_m(float(s.record["INTPTLON20"]), float(s.record["INTPTLAT20"])) ), s.record["HOUSING20"]))
blockpts = [(g, b[0], b[1]) for g, bs in blocks.items() for b in bs]
tree = STRtree([b[1] for b in blockpts])
served = {g: [0.0] * 24 for g in blocks}
for h in hours:
    if cover[h]:
        parts = list(cover[h].geoms) if hasattr(cover[h], "geoms") else [cover[h]]
        hit = set()
        for part in parts:
            hit.update(int(i) for i in tree.query(part, predicate="contains"))
        for i in hit:
            g, _, u = blockpts[i]
            served[g][h] += u

feats, rows = [], []
for g, p in tract_ll.items():
    pm = tract_m[g]
    units = sum(b[1] for b in blocks.get(g, [])) or 1
    cov = [round(served.get(g, [0] * 24)[h] / units, 4) for h in hours]
    dep = [0] * 24
    for k, s in stops.items():
        if not s["local"] and zones[k].intersects(pm):
            for h in hours:
                dep[h] += s["dep"][h]
    local = any(s["local"] and zones[k].intersects(pm) for k, s in stops.items())
    r = dict(g=g, name=f"Tract {int(g[5:9])}" + (f".{g[9:11]}" if g[9:] != "00" else ""), muni=muni[g],
             hh=round(hh.get(g, 0)), zero=round(zero.get(g, 0)), moe=round(zero_moe.get(g, 0)), cov=cov,
             dep=dep, local=local)
    rows.append(r)
    feats.append({"type": "Feature", "properties": r,
                  "geometry": mapping(p.simplify(0.0002, preserve_topology=True))})
routes_all = json.load(open(ROOT / "data/routes.json")) if (ROOT / "data/routes.json").exists() else {}
trips = collections.defaultdict(dict)
for k, v in routes_all.items():
    g, dn, h, mode = k.split("|")
    trips[g].setdefault(dn, {})[("car" if mode == "Car" else h)] = v
for f, r in zip(feats, rows):
    r["trips"] = trips.get(r["g"], {})
    f["properties"] = r
json.dump({"type": "FeatureCollection", "features": feats}, open(OUT / "tracts.geojson", "w"), separators=(",", ":"))

reachfeats = []
for h in hours:
    if cover[h]:
        g = transform(to_ll, cover[h]).simplify(0.0003).buffer(0)
        reachfeats.append({"type": "Feature", "properties": {"h": h}, "geometry": mapping(g)})
gj = {"type": "FeatureCollection", "features": reachfeats}
txt = json.dumps(gj, separators=(",", ":"))
import re
txt = re.sub(r"(\d+\.\d{4})\d+", r"\1", txt)
(OUT / "reach.geojson").write_text(txt)

Z = sum(r["zero"] for r in rows)
out_by_hour = [round(sum(r["zero"] * (1 - r["cov"][h]) for r in rows)) for h in hours]
dep_by_hour = [sum(s["dep"][h] for k, s in stops.items() if not s["local"] and county.contains(Point(s["xy"]))) for h in hours]
munis = []
for m in sorted({r["muni"] for r in rows}):
    rs = [r for r in rows if r["muni"] == m]
    z = sum(r["zero"] for r in rs)
    munis.append(dict(muni=m, tracts=len(rs), hh=sum(r["hh"] for r in rs), zero=z,
                      out=[round(sum(r["zero"] * (1 - r["cov"][h]) for r in rs)) for h in hours]))
summary = dict(households=sum(r["hh"] for r in rows), zero=Z, tracts=len(rows), out=out_by_hour, dep=dep_by_hour,
               munis=munis, meta=meta, acs=vintage, radius=RADIUS_M, isolines=iso_used, stops=len(stops),
               rt130hours=sorted(RT130_HOURS))
json.dump(summary, open(OUT / "summary.json", "w"), indent=1)
print(json.dumps({k: summary[k] for k in ("households", "zero", "tracts", "acs", "stops", "isolines", "meta")}))
print("hour  out_of_reach  pct  departures")
for h in hours:
    print(f"{h:>2}  {out_by_hour[h]:>6}  {100*out_by_hour[h]/Z:5.1f}  {dep_by_hour[h]}")
for m in sorted(munis, key=lambda m: -m["zero"]):
    print(m["muni"], m["tracts"], m["hh"], m["zero"], "out@8", m["out"][8], "out@23", m["out"][23], "out@1", m["out"][1])
for f in ("tracts.geojson", "reach.geojson", "summary.json"):
    print(f, (OUT / f).stat().st_size)
