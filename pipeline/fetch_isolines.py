#!/usr/bin/env python3
"""Fetch a 10-minute Pedestrian isoline for every stop with Amazon Location (cached per stop)."""
import concurrent.futures as cf, json, pathlib, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
ROOT = pathlib.Path(__file__).resolve().parent.parent
stops = json.load(open(ROOT / "data/stops.json"))
def get(item):
    k, (lon, lat) = item
    f = ROOT / "data/isolines" / f"{k}.json"
    if f.exists():
        return "cached"
    r = subprocess.run(["aws", "geo-routes", "calculate-isolines", "--region", "us-east-1", "--origin", str(lon), str(lat),
                        "--travel-mode", "Pedestrian", "--thresholds", '{"Time":[600]}', "--isoline-geometry-format", "Simple",
                        "--output", "json"], capture_output=True, text=True)
    if r.returncode:
        return "fail:" + r.stderr[:100]
    polys = [g["Polygon"] for i in json.loads(r.stdout)["Isolines"] for g in i["Geometries"]]
    f.write_text(json.dumps({"type": "MultiPolygon", "coordinates": polys}))
    return "ok"
with cf.ThreadPoolExecutor(10) as ex:
    res = list(ex.map(get, stops.items()))
import collections
print(collections.Counter(r[:60] for r in res))
