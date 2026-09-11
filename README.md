# Globe Jamun


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
- *Travel* — replays the journey in order, one leg at a time, with the camera
  riding along and a speed dropdown (2× / 5× / 10×). Grabbing the globe hands
  control straight back to you.
- *Auto-rotate* (off by default — the globe holds still until you ask), **+** / **&minus;**
  zoom, *Reset view*, and the **i** icon for the export guide
- The HUD lists every place, busiest first. Click a row to fly to it; clicking a
  marker on the globe highlights its row.

On phones the HUD starts collapsed to a title bar — tap the chevron to expand
the stats and legend. Place details open as a sheet above the controls, and the
initial camera altitude is derived from the viewport aspect so the globe fits a
portrait screen instead of overflowing it. You can also just open the site on
the phone holding the export and load the file directly, with no transfer.

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

## Travel playback

Every leg is stitched into one continuous path — consecutive legs meet at the
place between them, so the traveller crosses a leg boundary without a restart
or a seam. While it plays, the map's own route lines and rider icons are
cleared and a single trail draws itself in behind the traveller, so the journey
appears as you fly it. The camera height eases between travel modes, so a drive
rising into a flight reads as one movement rather than a cut.

The trail is revealed with the path's dash uniforms rather than by rebuilding
its geometry each frame — measured at 120fps during playback.

The map draws direct lines because they read better at a glance, but the
traveller follows the recorded GPS breadcrumbs where they exist — so playback
traces the real road while the overview stays legible. The whole journey takes
120s at 1x, divided by the chosen speed, so the run length does not balloon
with the size of your history.

## Place names

Visits are labelled by matching them against a GeoNames extract that ships with
the page (`web/cities.json`, ~34k places, 0.65 MB gzipped, lazy-loaded). This is
deliberately not a geocoding API call: sending your visit coordinates to a
reverse-geocoding service would hand a third party your home address, which is
the one thing this project promises not to do.

The match prefers a substantial nearby city over the literally-closest entry —
otherwise a Paris hotel resolves to "Paris 04 Hôtel-de-Ville" and a Dubai one to
"Business Bay". Rebuild with `python3 tools/build-cities.py`.

## Imagery

Far out, a single texture. Below ~0.55 globe radii the page switches to Esri
World Imagery tiles, which load only what is in view at a zoom matched to the
camera, and switches back on the way out. Attribution appears in the footer
while the tiles are live.

## Testing

`python3 tools/make-fixtures.py` builds a fixture set under `web/_t/`
(gitignored) covering the shapes the 13-place sample cannot: the iOS export
shape, a three-year history (~9.8k segments, 22MB), journeys with no GPS
breadcrumbs, visits with no journeys, routes crossing the antimeridian, and two
malformed files. Load each through the page and watch for uncaught errors — the
sample is too small and too tidy to catch performance or error-path problems.

## Debugging

Load the page with `#debug` to get a `window.__gj` handle exposing the globe,
its controls and the home-view calculation.

## Page views

The visit count in the HUD comes from [Abacus](https://github.com/jasoncameron/abacus)
— open source, no signup, no cookies, no identifiers, one integer against one key.
It is the only stateful thing this project touches. Local runs read the value
without incrementing it, and the line hides itself entirely if the service is
blocked or down, so nothing depends on it.

Caveat worth knowing: the key is public and guessable, so the number is a rough
indicator, not an audited metric. Anyone who finds the key could inflate it.

## Sample data

`data/Timeline.json` is synthetic: a Chennai-based year with commutes, drives to
Pondicherry and Coimbatore, flights to Bengaluru, Dubai, London, Paris and
Singapore. Regenerate with `python3 tools/make_sample_timeline.py`.
