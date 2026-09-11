# Global view

Live: https://aruntemme.github.io/globalview/

A 3D globe of everywhere you've been, built from Google Maps Timeline.
Free and open source end to end — no API keys, no accounts, no paid tiers.

## Stack

| Piece | What | Licence |
|---|---|---|
| globe.gl (three.js) | the globe, drag/rotate/zoom, arcs, trails | MIT |
| NASA Blue Marble imagery | earth texture | public domain |
| parser | plain Node, zero dependencies | — |

## Layout

    data/Timeline.sample.json   synthetic sample, committed
    data/Timeline.json          YOUR export — gitignored, never deployed
    data/routes.geojson         generated — gitignored
    tools/parse-timeline.mjs        normalizes an export
    tools/make_sample_timeline.py   regenerates the sample
    web/index.html              the globe
    web/journey.sample.json     sample build — this is what the hosted site ships
    web/journey.json            YOUR build — gitignored, never deployed

Only `web/` is deployed, and only the sample files in it are tracked. The page
loads `journey.json` if present and falls back to `journey.sample.json`, so the
hosted site always shows sample data and expects visitors to upload their own.

## Using your real data

The quickest route: open the page, click the **i** in the corner for the
export steps, then drag your `Timeline.json` onto the page. It is parsed in a
web worker in your browser — nothing is uploaded, and there is no server behind
the page.

To bake it in as the default instead:

1. Export from the phone:
   - **Android:** Settings → Location → Location services → Timeline → *Export Timeline data*
   - **iOS:** Maps → your avatar → Your Timeline → ⋯ → Location & privacy settings → *Export Timeline data*
2. Copy the file over `data/Timeline.json`.
3. `node tools/parse-timeline.mjs`
4. `python3 -m http.server 4173 --directory web` and open http://localhost:4173

The parser reads both the Android shape (`{semanticSegments: [...]}`, degree-sign
coordinates, `placeId`) and the iOS shape (bare array, `geo:` URIs, `placeID`,
distances as strings). Both produce identical output — verified against a
converted copy of the sample.

## Controls

- drag to rotate, scroll to zoom, right-drag to pan
- click a marker to fly to it and see visit stats
- *Load your Timeline.json* (or drop a file anywhere on the page)
- *GPS trails* — off by default, so road and rail draw as direct lines. Turn it
  on to follow the recorded breadcrumbs instead.
- *Auto-rotate*, *Reset view*, and the **i** icon for the export guide

## How records map to the globe

- `visit` → a marker, sized by total time spent there
- `activity` → a route, drawn by **travel family**

| Family | Modes | Drawn as | Icon |
|---|---|---|---|
| air | `FLYING` | lifted, dash-animated arc | plane |
| rail | train, subway, tram, ferry | flat dashed line on the surface | train |
| road | vehicle, bus, walking, cycling, everything else | flat solid line | car |

The family comes from the recorded mode, **never** from whether Google saved GPS
breadcrumbs for that segment. Only flights leave the ground, so a drive is never
mistaken for a flight.

Route curves are computed in `index.html` rather than handed to globe.gl's
`arcsData`, so each rider icon follows the exact same line it is drawn from
instead of approximating it. Direct lines still interpolate along a great circle
— a long straight segment would otherwise cut through the globe rather than lie
on it. Breadcrumbs are simplified to ~65 m in `timeline-core.js` to keep years
of tracking renderable.

## Code layout

`web/timeline-core.js` is imported by both the Node CLI and the browser worker,
so an uploaded file and a `node tools/parse-timeline.mjs` run go through
identical normalization.

## Sample data

`data/Timeline.json` is synthetic: a Chennai-based year with commutes, drives to
Pondicherry and Coimbatore, flights to Bengaluru, Dubai, London, Paris and
Singapore. Regenerate with `python3 tools/make_sample_timeline.py`.
