# Desert Hours

An hourly map of who can walk to scheduled transit in Mercer County, NJ. Entry for the AWS Builder Center Weekend Challenge: Map It.

**Live:** https://d35zkoavyfqlat.cloudfront.net/

Car-free households out of reach: 6,388 of 16,114 at 8 AM, 14,095 at 3 AM.

| Path | What it does |
|---|---|
| `pipeline/build_data.py` | Hourly reach by tract, from GTFS, Census and isolines. Every figure on the site comes from here. |
| `pipeline/fetch_isolines.py` | 10-minute Pedestrian isoline per stop (Amazon Location, cached) |
| `pipeline/fetch_routes.py` | Transit and car journeys per tract (Amazon Location, cached) |
| `pipeline/build_site.py` | Fills `site/template.html` so the findings read without JavaScript |
| `deploy/` | CloudFormation stack (private S3, CloudFront), deploy and demo recording |

Inputs go in `data/raw`, which is not committed: NJ TRANSIT GTFS, Census Reporter table B08201, TIGER tract, county subdivision and 2020 block files, and Mercer County's Route 130 stop layer. Python packages: `pyshp`, `shapely`. `site/config.js` holds the map key and is not committed; the key is limited to `geo-maps` actions and this site's domain.

Scheduled service only; may be incomplete, inaccurate or out of date. Independent of NJ TRANSIT. Code is Apache-2.0.
