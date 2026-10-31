---
title: "Desert Hours: Mapping When Mercer County's Transit Disappears"
published: false
description: "An hourly Amazon Location Service map of who can walk to scheduled transit in Mercer County, NJ. 6,388 car-free households are out of reach at 8 AM and 14,095 at 3 AM."
tags: amazon-location-service, amazon-s3, amazon-cloudfront
---

A transit desert can open and close in a single day. In Mercer County, New Jersey, 6,388 households without a car are out of walking reach of scheduled service at 8 AM. By 3 AM that number is 14,095, of 16,114 car-free households in the county.

**Live map:** https://d35zkoavyfqlat.cloudfront.net/

**Demo video:** https://youtu.be/jfC_d6nq2EM

#### What You Can Explore

Drag the clock from 5 AM to 4 AM and the blue walkable service area shrinks across the county. Click any census tract to see its car-free households, how much of its housing can reach service at that hour, its departures through the day, and how long three everyday trips take by transit at 8 AM, 5 PM, 11 PM and 2 AM against driving.

---

#### The Dataset

| Source | What it holds | Use |
| --- | --- | --- |
| NJ TRANSIT GTFS | Scheduled bus and rail departures | Departures per stop, per hour, on one Wednesday |
| Census ACS table B08201 (2024 5-year) | Households by vehicles available | 16,114 car-free households of 144,114 |
| 2020 Census blocks | Housing units per block | Where a tract's households sit |
| Mercer County route layer | Route 130 Connection stops | A county service outside the NJ TRANSIT feed |

All published figures are county, municipal or tract totals, so the map holds no personal data.

---

#### How the Data Reaches the Map

Step 1 — Count scheduled departures for each of 1,012 stops, by hour, from the GTFS files.

Step 2 — Ask Amazon Location for a 10-minute walk from every stop.

```bash
aws geo-routes calculate-isolines --region us-east-1 \
  --origin -74.7548 40.2186 --travel-mode Pedestrian \
  --thresholds '{"Time":[600]}' --isoline-geometry-format Simple
```

Step 3 — For each hour, join the walking areas of the stops with a departure in that hour into one service area.

Step 4 — Test each Census block against that area and carry its share of the tract's car-free households. A tract's total is spread across blocks by housing units.

Step 5 — Ask Amazon Location Routes for transit and driving times from a point in each tract to three destinations.

```bash
aws geo-routes calculate-routes --region us-east-1 \
  --origin -74.7548 40.2186 --destination -74.6672 40.3495 \
  --travel-mode Transit --departure-time 2026-11-04T02:00:00-05:00
```

Step 6 — Serve the results as static files from a private Amazon S3 bucket through Amazon CloudFront, and draw them with MapLibre over an Amazon Location base map.

---

#### Why Amazon Location Service

Walking reach follows streets. A circle treats a cul-de-sac and a city grid the same. At three Mercer test points, a 10-minute Pedestrian isoline covered 0.33 km² at Trenton station and 0.09 km² in a Hamilton suburb, at about the same straight-line distance from the origin.

`CalculateRoutes` returns timetable journeys in `Transit` mode, so a tract's 2 AM row shows the real departure and arrival times. Maps, isolines and routes share one service and one set of credentials, which kept the whole pipeline to a few short scripts.

---

#### One Tract, One Day

Trenton Tract 1 has about 445 car-free households of 1,332 (margin ±227).

| Measure | Result |
| --- | --- |
| Housing within a 10-minute walk of service, 8 AM | 73% |
| Housing within a 10-minute walk of service, 11 PM | 0% |
| Drive to Capital Health Regional Medical Center | 11 minutes |
| Transit to the hospital, leaving at 8 AM | 52 minutes |
| Transit to the hospital, leaving at 2 AM | 3 hours 29 minutes |

---

#### Scope

The map shows scheduled service for one weekday and may be incomplete, inaccurate or out of date. TigerTransit, the Princeton municipal shuttle, the Z-Line and on-demand services are not included, so reach is understated where they run. Route 130 Connection stops use a September 2023 timetable and count in every hour with a departure, which favors the route. Car-free households are assumed to be spread like housing within a tract, and tract estimates carry wide margins. Schedule data comes from NJ TRANSIT's published GTFS through the Mobility Database archive. This project is independent of NJ TRANSIT.

#### References

- [Live map](https://d35zkoavyfqlat.cloudfront.net/)
- [Code on GitHub](https://github.com/xbill9/desert-hours)
- [Amazon Location Service CalculateIsolines](https://docs.aws.amazon.com/location/latest/APIReference/API_CalculateIsolines.html)
- [Amazon Location Service CalculateRoutes](https://docs.aws.amazon.com/location/latest/APIReference/API_CalculateRoutes.html)
- [Transit Deserts method](https://transitdeserts.info/about.html)
