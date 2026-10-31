#!/usr/bin/env python3
"""Transit and car journeys from each tract's interior point to three destinations (cached)."""
import concurrent.futures as cf, datetime as dt, json, pathlib, subprocess, sys
import shapefile
from shapely.geometry import shape
ROOT = pathlib.Path(__file__).resolve().parent.parent
DEST = json.loads(sys.argv[1])
HOURS = [8, 17, 23, 2]
DAY = "2026-11-04"
OUT = ROOT / "data/routes.json"
done = json.load(open(OUT)) if OUT.exists() else {}
r = shapefile.Reader(str(ROOT / "data/raw/geo/tl_2023_34_tract.shp"), encoding="utf-8")
pts = {s.record["GEOID"]: shape(s.shape.__geo_interface__).representative_point() for s in r.iterShapeRecords() if s.record["COUNTYFP"] == "021"}
def call(mode, o, d, t):
    c = subprocess.run(["aws", "geo-routes", "calculate-routes", "--region", "us-east-1", "--origin", str(o.x), str(o.y), "--destination", str(d[0]), str(d[1]),
                        "--travel-mode", mode, "--departure-time", t, "--output", "json"], capture_output=True, text=True)
    return json.loads(c.stdout) if c.returncode == 0 else {"error": c.stderr[-160:]}
def job(j):
    key, g, dn, h, mode = j
    if key in done:
        return None
    t = f"{DAY}T{h:02d}:00:00-05:00"
    x = call(mode, pts[g], DEST[dn], t)
    if "error" in x or not x.get("Routes"):
        return key, {"none": True, "err": x.get("error", "no route")[:120]}
    rt = x["Routes"][0]
    if mode == "Car":
        return key, {"min": round(rt["Summary"]["Duration"] / 60), "km": round(rt["Summary"]["Distance"] / 1000, 1)}
    tm = []
    modes = []
    for l in rt["Legs"]:
        det = l.get("TransitLegDetails") or l.get("PedestrianLegDetails") or {}
        for side in ("Departure", "Arrival"):
            if det.get(side, {}).get("Time"):
                tm.append(det[side]["Time"])
        if l["Type"] == "Transit":
            modes.append(l["TravelMode"])
    a = dt.datetime.fromisoformat(max(tm))
    s = dt.datetime.fromisoformat(min(tm))
    return key, {"min": round((a - dt.datetime.fromisoformat(t)).total_seconds() / 60), "wait": round((s - dt.datetime.fromisoformat(t)).total_seconds() / 60),
                 "arrive": a.strftime("%-I:%M %p"), "leave": s.strftime("%-I:%M %p"), "km": round(rt["Summary"]["Distance"] / 1000, 1), "modes": modes}
jobs = [(f"{g}|{dn}|{h}|Transit", g, dn, h, "Transit") for g in pts for dn in DEST for h in HOURS]
jobs += [(f"{g}|{dn}|8|Car", g, dn, 8, "Car") for g in pts for dn in DEST]
with cf.ThreadPoolExecutor(10) as ex:
    for res in ex.map(job, jobs):
        if res:
            done[res[0]] = res[1]
json.dump(done, open(OUT, "w"))
print(len(done), "none", sum("none" in v for v in done.values()))
print([v.get("err") for v in done.values() if "none" in v][:3])
