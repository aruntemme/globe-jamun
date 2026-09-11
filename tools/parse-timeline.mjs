#!/usr/bin/env node
// Normalize an on-device Google Timeline export into globe-ready data.
// Usage: node tools/parse-timeline.mjs [data/Timeline.json]
// The browser upload path uses the same core module.

import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { resolve, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseTimeline } from '../web/timeline-core.js';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
// Your real export is data/Timeline.json (gitignored). Falls back to the
// committed sample so a fresh clone works with no setup.
const fallback = existsSync(join(root, 'data', 'Timeline.json'))
  ? join(root, 'data', 'Timeline.json')
  : join(root, 'data', 'Timeline.sample.json');
const input = resolve(process.argv[2] ?? fallback);
const isSample = input.endsWith('Timeline.sample.json');

let journey;
try {
  journey = parseTimeline(JSON.parse(readFileSync(input, 'utf8')));
} catch (err) {
  console.error(`${input}: ${err.message}`);
  process.exit(1);
}
journey.generatedAt = new Date().toISOString();
journey.source = input.split('/').pop();

const { places, trails, arcs } = journey;
const geojson = {
  type: 'FeatureCollection',
  features: [
    ...places.map((p) => ({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [p.lng, p.lat] },
      properties: {
        semanticType: p.semanticType, visits: p.visits,
        minutes: p.minutes, firstSeen: p.firstSeen, lastSeen: p.lastSeen,
      },
    })),
    ...trails.map((t) => ({
      type: 'Feature',
      geometry: { type: 'LineString', coordinates: t.path.map(([la, ln]) => [ln, la]) },
      properties: { mode: t.mode, km: t.km, startTime: t.startTime, endTime: t.endTime },
    })),
    ...arcs.map((a) => ({
      type: 'Feature',
      geometry: { type: 'LineString', coordinates: [[a.startLng, a.startLat], [a.endLng, a.endLat]] },
      properties: { mode: a.mode, km: a.km, startTime: a.startTime, endTime: a.endTime, synthetic: true },
    })),
  ],
};

// Sample runs refresh the deployable file; personal runs write the ignored one.
const outJourney = join(root, 'web', isSample ? 'journey.sample.json' : 'journey.json');
const outGeo = join(root, 'data', 'routes.geojson');
writeFileSync(outJourney, JSON.stringify(journey));
writeFileSync(outGeo, JSON.stringify(geojson));

const totalKm = [...trails, ...arcs].reduce((s, r) => s + r.km, 0);
console.log(`read    ${input}`);
console.log(`  format        ${journey.format}`);
console.log(`  segments      ${journey.segmentCount}`);
console.log(`  places        ${places.length} unique`);
console.log(`  trails        ${trails.length} (${trails.reduce((s, t) => s + t.path.length, 0)} points)`);
console.log(`  arcs          ${arcs.length}`);
console.log(`  distance      ${Math.round(totalKm).toLocaleString()} km`);
console.log(`  range         ${journey.range.from?.slice(0, 10)} .. ${journey.range.to?.slice(0, 10)}`);
if (journey.skipped) console.log(`  skipped       ${journey.skipped} unparseable segment(s)`);
console.log(`wrote   ${outJourney}`);
console.log(`wrote   ${outGeo}`);
