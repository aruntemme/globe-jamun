// Shared normalization for on-device Google Timeline exports.
// Runs unchanged in Node (tools/parse-timeline.mjs) and in the browser worker,
// so an uploaded file goes through exactly the same path as a CLI run.

// Android: "13.0067°, 80.2206°"   iOS: "geo:13.0067,80.2206"
export function parseLatLng(raw) {
  if (raw == null) return null;
  const s = typeof raw === 'string' ? raw : raw.latLng ?? raw.point ?? null;
  if (typeof s !== 'string') return null;
  const m = s.replace(/^geo:/, '').match(/(-?\d+(?:\.\d+)?)\s*°?\s*,\s*(-?\d+(?:\.\d+)?)/);
  if (!m) return null;
  const lat = Number(m[1]), lng = Number(m[2]);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
  if (Math.abs(lat) > 90 || Math.abs(lng) > 180) return null;
  return [lat, lng];
}

const num = (v) => (typeof v === 'string' ? Number(v) : v) || 0;
const minutesBetween = (a, b) => Math.max(0, (Date.parse(b) - Date.parse(a)) / 60000);

export function haversineKm([lat1, lng1], [lat2, lng2]) {
  const R = 6371.0088, r = Math.PI / 180;
  const dLat = (lat2 - lat1) * r, dLng = (lng2 - lng1) * r;
  const h = Math.sin(dLat / 2) ** 2
    + Math.cos(lat1 * r) * Math.cos(lat2 * r) * Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.asin(Math.sqrt(h));
}

// Perpendicular-distance simplification. Years of breadcrumbs can run to
// hundreds of thousands of points; the globe only needs the shape.
export function simplify(points, toleranceDeg) {
  if (points.length < 3) return points;
  const keep = new Uint8Array(points.length);
  keep[0] = keep[points.length - 1] = 1;
  const stack = [[0, points.length - 1]];
  while (stack.length) {
    const [lo, hi] = stack.pop();
    if (hi - lo < 2) continue;
    const [ax, ay] = points[lo], [bx, by] = points[hi];
    const dx = bx - ax, dy = by - ay;
    const denom = Math.hypot(dx, dy) || 1;
    let far = -1, farIdx = -1;
    for (let i = lo + 1; i < hi; i++) {
      const [px, py] = points[i];
      const d = Math.abs(dy * px - dx * py + bx * ay - by * ax) / denom;
      if (d > far) { far = d; farIdx = i; }
    }
    if (far > toleranceDeg) {
      keep[farIdx] = 1;
      stack.push([lo, farIdx], [farIdx, hi]);
    }
  }
  return points.filter((_, i) => keep[i]);
}

const placeKey = (id, [lat, lng]) => id ?? `@${lat.toFixed(3)},${lng.toFixed(3)}`;

/**
 * @param {object|Array} raw  parsed Timeline.json (Android object or iOS array)
 * @param {(pct:number)=>void} [onProgress]
 */
export function parseTimeline(raw, onProgress) {
  const segments = Array.isArray(raw) ? raw : raw?.semanticSegments ?? [];
  if (!segments.length) {
    throw new Error('No segments found. This does not look like an on-device Timeline export.');
  }

  const places = new Map();
  const trails = [];
  const arcs = [];
  let skipped = 0;

  segments.forEach((seg, i) => {
    if (onProgress && i % 5000 === 0) onProgress(i / segments.length);
    const { startTime, endTime } = seg;
    if (!startTime) { skipped++; return; }

    if (seg.visit) {
      const c = seg.visit.topCandidate ?? {};
      const coord = parseLatLng(c.placeLocation);
      if (!coord) { skipped++; }
      else {
        const id = c.placeId ?? c.placeID ?? null;   // iOS capitalizes the D
        const key = placeKey(id, coord);
        const stay = minutesBetween(startTime, endTime ?? startTime);
        const prev = places.get(key);
        if (prev) {
          prev.visits += 1;
          prev.minutes += stay;
          if (startTime < prev.firstSeen) prev.firstSeen = startTime;
          if (startTime > prev.lastSeen) prev.lastSeen = startTime;
        } else {
          places.set(key, {
            id: key, lat: coord[0], lng: coord[1],
            semanticType: c.semanticType ?? 'Inferred',
            visits: 1, minutes: stay, firstSeen: startTime, lastSeen: startTime,
          });
        }
      }
    }

    if (seg.activity) {
      const a = seg.activity;
      const from = parseLatLng(a.start);
      const to = parseLatLng(a.end);
      if (!from || !to) { skipped++; return; }
      const mode = a.topCandidate?.type ?? 'UNKNOWN';
      const km = num(a.distanceMeters) / 1000 || haversineKm(from, to);

      // Real breadcrumbs beat a synthetic line. Fall back to an arc when absent.
      let path = (seg.timelinePath ?? []).map((p) => parseLatLng(p.point ?? p)).filter(Boolean);
      if (path.length >= 2 && mode !== 'FLYING') {
        if (path.length > 24) path = simplify(path, 0.0006);  // ~65 m
        trails.push({ mode, km, startTime, endTime, path });
      } else {
        arcs.push({
          mode, km, startTime, endTime,
          startLat: from[0], startLng: from[1], endLat: to[0], endLng: to[1],
        });
      }
    }
  });

  const placeList = [...places.values()]
    .map((p) => ({ ...p, minutes: Math.round(p.minutes) }))
    .sort((a, b) => b.minutes - a.minutes);

  const times = segments.map((s) => s.startTime).filter(Boolean).sort();
  onProgress?.(1);

  return {
    range: { from: times[0] ?? null, to: times[times.length - 1] ?? null },
    format: Array.isArray(raw) ? 'iOS' : 'Android',
    segmentCount: segments.length,
    skipped,
    places: placeList,
    trails,
    arcs,
  };
}
