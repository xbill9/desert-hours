# Desert Hours: Mapping When Transit Disappears With Amazon Location Service

This article provides a step by step guide to building an hourly transit reach map with Amazon Location Service. Walking areas come from Pedestrian isolines, journey times come from Transit routing, and the finished map runs as static files on Amazon S3 and Amazon CloudFront.

Repository: https://github.com/xbill9/desert-hours

Live map: https://d35zkoavyfqlat.cloudfront.net/

Demo video: [Watch the demo on YouTube](https://youtu.be/jfC_d6nq2EM)

---

#### What Is a Transit Desert?

A transit desert is a place where demand for transit outruns the service on offer. Published maps usually score that gap once per area. Service changes by the hour, so this project scores it for every hour of a weekday.

The study area is Mercer County, New Jersey. It holds Trenton, Princeton and a ring of suburbs, and 16,114 of its 144,114 households have no car.

---

#### What You Can Explore

Drag the clock from 5 AM to 4 AM and the blue walkable service area shrinks across the county. The running total shows how many car-free households are out of reach at that hour.

Click a census tract for its day: car-free households, the share of housing that can reach service, departures by hour, and transit times to three destinations at 8 AM, 5 PM, 11 PM and 2 AM beside the driving time.

---

#### At This Point You Should Have

- An AWS account with access to Amazon Location Service
- The AWS CLI, version 2
- Python 3 with `pyshp` and `shapely`
- A GTFS feed for your area, a car ownership table and Census block boundaries

---

#### Step 1 — Gather the Data

| Source | What it holds | Use |
| --- | --- | --- |
| NJ TRANSIT GTFS | Scheduled bus and rail departures | Departures per stop, per hour |
| Census ACS table B08201 | Households by vehicles available | Car-free households per tract |
| 2020 Census blocks | Housing units per block | Where households sit in a tract |
| Mercer County route layer | Route 130 Connection stops | A county service outside the feed |

Every published figure is a county, municipal or tract total, so the map holds no personal data.

---

#### Step 2 — Count Departures by Hour

`pipeline/build_data.py` picks one Wednesday in the feed and counts departures per stop in each hour. It keeps stops inside the county and within 1.5 km of it, because people cross county lines to catch a bus. That leaves 1,012 stops.

---

#### Step 3 — Ask Amazon Location for a 10-Minute Walk

Each stop gets a Pedestrian isoline along the street network.

```bash
aws geo-routes calculate-isolines --region us-east-1 \
  --origin -74.7548 40.2186 --travel-mode Pedestrian \
  --thresholds '{"Time":[600]}' --isoline-geometry-format Simple
```

The shape depends on the streets around the stop. Both of these reach about 560 m at their farthest point:

| Location | 10-minute walk area | Farthest point |
| --- | --- | --- |
| Trenton station | 0.33 km² | 562 m |
| Hamilton suburb | 0.09 km² | 560 m |

The median across all 1,012 stops is 0.26 km², against 0.50 km² for a 400 m circle.

---

####  Tip: Place Households Where Housing Is

A tract includes parks, rail yards and farmland. Spreading its households evenly across that area counts people who live nowhere near those spaces.

Census blocks carry a housing unit count, so each tract's car-free households are shared across its blocks by housing units. A block counts as served in an hour when its interior point falls inside that hour's service area.

---

#### Step 4 — Build the Hourly Service Area

For each hour, the pipeline joins the walking areas of the stops with at least one departure in that hour. Testing every block against that shape gives the hourly total.

Code does the counting and the page quotes it:

| Hour | Car-free households out of reach | Share |
| --- | --- | --- |
| 8 AM | 6,388 | 39.6% |
| 11 PM | 8,129 | 50.4% |
| 3 AM | 14,095 | 87.5% |

---

#### Step 5 — Ask for Real Journeys

`CalculateIsolines` covers walking and driving modes. `CalculateRoutes` adds a `Transit` mode with timetable departures.

```bash
aws geo-routes calculate-routes --region us-east-1 \
  --origin -74.7548 40.2186 --destination -74.6672 40.3495 \
  --travel-mode Transit --departure-time 2026-11-04T02:00:00-05:00
```

A request for 2 AM from Trenton to Princeton returns a timed journey:

| Leg | Departs | Arrives |
| --- | --- | --- |
| Walk to Trenton Transit Center | 3:56 AM | 4:11 AM |
| Train to Princeton Junction | 4:11 AM | 4:24 AM |
| Train to Princeton | 4:40 AM | 4:45 AM |
| Walk to the destination | 4:45 AM | 5:09 AM |

The trip takes 3 hours 9 minutes from the moment you wanted to leave, and most of that is waiting for the first train. The pipeline stores that full wait.

---

#### Step 6 — Ship It as Static Files

The results are GeoJSON and HTML in a private S3 bucket behind CloudFront. Precomputing everything leaves the page with one Amazon Location key, limited to map actions and the site's domain.

```bash
aws cloudformation deploy --region us-east-1 \
  --stack-name desert-hours --template-file deploy/stack.yaml
```

The findings sit in the page's HTML, so they read without JavaScript. MapLibre draws the tracts and service areas over an Amazon Location base map.

---

#### One Tract, One Day

Trenton Tract 1 is a strip along the Delaware River with about 445 car-free households of 1,332, with a margin of ±227.

| Measure | Result |
| --- | --- |
| Housing within a 10-minute walk of service, 8 AM | 73% |
| Housing within a 10-minute walk of service, 11 PM | 0% |
| Drive to Capital Health Regional Medical Center | 11 minutes |
| Transit to the hospital, leaving at 8 AM | 52 minutes |
| Transit to the hospital, leaving at 2 AM | 3 hours 29 minutes |

---

#### Compare and Contrast

| Approach | Walking area | Time of day | Journey times |
| --- | --- | --- | --- |
| 400 m circles | Same everywhere | Any | None |
| Static desert score | Varies by method | One score | None |
| Desert Hours | Street network | Every hour | Timetable by Amazon Location |

---

#### What Did It Cost?

| Item | Count | List price | Total |
| --- | --- | --- | --- |
| Isolines | 1,012 | $1.50 per thousand | $1.52 |
| Journeys | 1,260 | $0.50 per thousand | $0.63 |

Totals are arithmetic from AWS Price List rates. Results are cached, so a rebuild makes no new calls.

---

#### So, Which One?

Use isolines when reach depends on the street network, which it does in any suburb. Use Transit routing for the stories a map shape cannot tell, such as how long a 2 AM trip takes. Keep both in a batch pipeline, and the live page never spends money on routing.

---

#### Summary

The goal of this article was to map how transit reach changes through a weekday. The key to the solution was Amazon Location Pedestrian isolines joined by hour and tested against Census blocks. The Mercer County results were:

- 6,388 car-free households are out of walking reach at 8 AM, 39.6% of the county's total
- 14,095 are out of reach at 3 AM, 87.5% of the total
- Street-based walking areas separate a city grid from a suburb at the same distance
- Trenton Tract 1 falls from 73% of housing in reach at 8 AM to 0% at 11 PM

Scope: scheduled service for one weekday, which may be incomplete, inaccurate or out of date. TigerTransit, the Princeton municipal shuttle, the Z-Line and on-demand services are not included, so reach is understated where they run. Route 130 Connection stops use a September 2023 timetable and count in every hour with a departure. Car-free households are assumed to be spread like housing within a tract, and tract estimates carry wide margins. Journey times come from one point per tract. Schedule data comes from NJ TRANSIT's published GTFS through the Mobility Database archive, and this project is independent of NJ TRANSIT.

The strategy for using Amazon Location Service for an hourly transit map was validated with an incremental step by step approach.

#### References

- [Live map](https://d35zkoavyfqlat.cloudfront.net/)
- [Code on GitHub](https://github.com/xbill9/desert-hours)
- [Demo video](https://youtu.be/jfC_d6nq2EM)
- [CalculateIsolines API](https://docs.aws.amazon.com/location/latest/APIReference/API_CalculateIsolines.html)
- [CalculateRoutes API](https://docs.aws.amazon.com/location/latest/APIReference/API_CalculateRoutes.html)
- [Transit Deserts method](https://transitdeserts.info/about.html)
