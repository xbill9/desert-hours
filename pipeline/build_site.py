#!/usr/bin/env python3
"""Fill site/template.html with computed figures so the findings are readable without JavaScript."""
import json, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
S = json.load(open(ROOT / "site/data/summary.json"))
T = {f["properties"]["g"]: f["properties"] for f in json.load(open(ROOT / "site/data/tracts.geojson"))["features"]}
t1 = T["34021000100"]; hosp = t1["trips"]["Capital Health Regional Medical Center"]
c = lambda n: f"{n:,}"
def name(h):
    x = h % 12 or 12
    return "Noon" if h == 12 else "Midnight" if h == 0 else f"{x} {'AM' if h < 12 else 'PM'}"
def dur(m): return f"{m//60} hours {m%60} minutes" if m >= 60 else f"{m} minutes"
rows = "".join(f"<tr><td>{m['muni']}</td><td>{c(m['zero'])}</td><td>{c(m['out'][8])}</td><td>{c(m['out'][23])}</td><td>{c(m['out'][3])}</td></tr>" for m in sorted(S["munis"], key=lambda m: -m["zero"]))
hours = "".join(f"<tr><td>{name(h%24)}</td><td>{c(S['out'][h%24])}</td><td>{100*S['out'][h%24]/S['zero']:.1f}%</td><td>{c(S['dep'][h%24])}</td></tr>" for h in range(5, 29))
d = S["meta"]["bus"]["day"]
v = dict(out8=c(S["out"][8]), out23=c(S["out"][23]), out3=c(S["out"][3]), zero=c(S["zero"]), hh=c(S["households"]), tracts=S["tracts"], stops=c(S["stops"]),
         rows=rows, hours=hours, day=f"November {int(d[6:])}, {d[:4]}", acs=S["acs"], t1zero=t1["zero"], t1hh=c(t1["hh"]), t1moe=t1["moe"],
         t1cov8=round(t1["cov"][8]*100), t1cov23=round(t1["cov"][23]*100), t1car=hosp["car"]["min"], t1t8=hosp["8"]["min"], t12h=dur(hosp["2"]["min"]), t12leave=hosp["2"]["leave"])
t = (ROOT / "site/template.html").read_text()
for k, x in v.items():
    t = t.replace("{{" + k + "}}", str(x))
assert "{{" not in t
(ROOT / "site/index.html").write_text(t)
