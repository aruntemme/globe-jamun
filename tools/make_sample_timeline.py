"""Generate a realistic sample Timeline.json in the on-device Android export shape.

Drop the real export over data/Timeline.json when you have it; the parser reads
both this sample and the genuine Android/iOS files.
"""
import json
import math
import os
import random
from datetime import datetime, timedelta, timezone

random.seed(20260911)

IST = timezone(timedelta(hours=5, minutes=30))

PLACES = {
    "home":        (13.0067, 80.2206, "Home", "ChIJ_sample_home_adyar"),
    "office":      (12.9915, 80.2337, "Work", "ChIJ_sample_office_guvi"),
    "maa_airport": (12.9941, 80.1709, "Airport", "ChIJ_sample_maa"),
    "pondicherry": (11.9416, 79.8083, "Inferred", "ChIJ_sample_pondy"),
    "blr":         (12.9716, 77.5946, "Inferred", "ChIJ_sample_blr"),
    "coimbatore":  (11.0168, 76.9558, "Inferred", "ChIJ_sample_cbe"),
    "dxb":         (25.2532, 55.3657, "Airport", "ChIJ_sample_dxb"),
    "dubai_hotel": (25.1972, 55.2744, "Inferred", "ChIJ_sample_burj"),
    "lhr":         (51.4700, -0.4543, "Airport", "ChIJ_sample_lhr"),
    "london":      (51.5072, -0.1276, "Inferred", "ChIJ_sample_london"),
    "paris":       (48.8566, 2.3522, "Inferred", "ChIJ_sample_paris"),
    "sin":         (1.3644, 103.9915, "Airport", "ChIJ_sample_sin"),
    "singapore":   (1.2834, 103.8607, "Inferred", "ChIJ_sample_sg"),
}


def fmt_latlng(lat, lng):
    """Android writes decimal degrees with a degree sign on each component."""
    return f"{lat:.7f}°, {lng:.7f}°"


def haversine_m(a, b):
    lat1, lng1 = math.radians(a[0]), math.radians(a[1])
    lat2, lng2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlng = lat2 - lat1, lng2 - lng1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 6371008.8 * 2 * math.asin(math.sqrt(h))


def great_circle(a, b, n):
    """Interpolate n points along the great circle from a to b."""
    lat1, lng1 = math.radians(a[0]), math.radians(a[1])
    lat2, lng2 = math.radians(b[0]), math.radians(b[1])
    d = 2 * math.asin(math.sqrt(
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2))
    if d == 0:
        return [a] * n
    out = []
    for i in range(n):
        f = i / (n - 1)
        A = math.sin((1 - f) * d) / math.sin(d)
        B = math.sin(f * d) / math.sin(d)
        x = A * math.cos(lat1) * math.cos(lng1) + B * math.cos(lat2) * math.cos(lng2)
        y = A * math.cos(lat1) * math.sin(lng1) + B * math.cos(lat2) * math.sin(lng2)
        z = A * math.sin(lat1) + B * math.sin(lat2)
        out.append((math.degrees(math.atan2(z, math.hypot(x, y))),
                    math.degrees(math.atan2(y, x))))
    return out


def road_path(a, b, n, wobble):
    """A ground route: great circle nudged sideways so it reads like a real road."""
    pts = great_circle(a, b, n)
    out = []
    for i, (lat, lng) in enumerate(pts):
        f = i / (n - 1)
        bulge = math.sin(f * math.pi) * wobble
        out.append((lat + bulge * random.uniform(0.4, 1.0),
                    lng + bulge * random.uniform(-1.0, 1.0)))
    out[0], out[-1] = pts[0], pts[-1]
    return out


segments = []


def add_visit(key, start, minutes):
    lat, lng, semantic, place_id = PLACES[key]
    end = start + timedelta(minutes=minutes)
    segments.append({
        "startTime": start.isoformat(),
        "endTime": end.isoformat(),
        "startTimeTimezoneUtcOffsetMinutes": int(start.utcoffset().total_seconds() // 60),
        "endTimeTimezoneUtcOffsetMinutes": int(end.utcoffset().total_seconds() // 60),
        "visit": {
            "hierarchyLevel": 0,
            "probability": round(random.uniform(0.74, 0.99), 2),
            "topCandidate": {
                "placeId": place_id,
                "semanticType": semantic,
                "probability": round(random.uniform(0.62, 0.98), 2),
                "placeLocation": {"latLng": fmt_latlng(lat, lng)},
            },
        },
    })
    return end


def add_activity(from_key, to_key, start, minutes, mode, breadcrumbs=0, wobble=0.0):
    a = PLACES[from_key][:2]
    b = PLACES[to_key][:2]
    end = start + timedelta(minutes=minutes)
    seg = {
        "startTime": start.isoformat(),
        "endTime": end.isoformat(),
        "startTimeTimezoneUtcOffsetMinutes": int(start.utcoffset().total_seconds() // 60),
        "endTimeTimezoneUtcOffsetMinutes": int(end.utcoffset().total_seconds() // 60),
        "activity": {
            "start": {"latLng": fmt_latlng(*a)},
            "end": {"latLng": fmt_latlng(*b)},
            "distanceMeters": round(haversine_m(a, b), 1),
            "topCandidate": {
                "type": mode,
                "probability": round(random.uniform(0.55, 0.97), 2),
            },
        },
    }
    if breadcrumbs:
        pts = road_path(a, b, breadcrumbs, wobble)
        seg["timelinePath"] = [
            {
                "point": fmt_latlng(lat, lng),
                "durationMinutesOffsetFromStartTime": str(
                    round(minutes * i / (breadcrumbs - 1))),
            }
            for i, (lat, lng) in enumerate(pts)
        ]
    segments.append(seg)
    return end


t = datetime(2025, 1, 14, 7, 40, tzinfo=IST)

# --- Chennai routine: a few commutes so the home cluster looks lived-in ---
for day in range(4):
    d = t + timedelta(days=day)
    cur = add_visit("home", d, 20)
    cur = add_activity("home", "office", cur, 42, "IN_PASSENGER_VEHICLE", 26, 0.010)
    cur = add_visit("office", cur, 520)
    cur = add_activity("office", "home", cur, 51, "IN_PASSENGER_VEHICLE", 26, 0.010)
    cur = add_visit("home", cur, 760)

# --- Weekend drive to Pondicherry ---
t = datetime(2025, 1, 25, 6, 15, tzinfo=IST)
t = add_activity("home", "pondicherry", t, 195, "IN_PASSENGER_VEHICLE", 90, 0.055)
t = add_visit("pondicherry", t, 1680)
t = add_activity("pondicherry", "home", t, 210, "IN_PASSENGER_VEHICLE", 90, 0.048)
t = add_visit("home", t, 600)

# --- Bengaluru hop by air ---
t = datetime(2025, 2, 6, 5, 30, tzinfo=IST)
t = add_activity("home", "maa_airport", t, 38, "IN_PASSENGER_VEHICLE", 20, 0.008)
t = add_visit("maa_airport", t, 95)
t = add_activity("maa_airport", "blr", t, 60, "FLYING", 14, 0.0)
t = add_visit("blr", t, 2200)
t = add_activity("blr", "maa_airport", t, 65, "FLYING", 14, 0.0)
t = add_visit("home", t, 900)

# --- Coimbatore road trip ---
t = datetime(2025, 3, 8, 5, 50, tzinfo=IST)
t = add_activity("home", "coimbatore", t, 420, "IN_PASSENGER_VEHICLE", 140, 0.070)
t = add_visit("coimbatore", t, 2600)
t = add_activity("coimbatore", "home", t, 445, "IN_PASSENGER_VEHICLE", 140, 0.065)
t = add_visit("home", t, 1200)

# --- The long one: Chennai to Dubai to London to Paris and back ---
t = datetime(2025, 5, 2, 1, 10, tzinfo=IST)
t = add_activity("home", "maa_airport", t, 30, "IN_PASSENGER_VEHICLE", 18, 0.006)
t = add_visit("maa_airport", t, 130)
t = add_activity("maa_airport", "dxb", t, 265, "FLYING", 40, 0.0)
t = add_visit("dxb", t, 90)
t = add_activity("dxb", "dubai_hotel", t, 35, "IN_PASSENGER_VEHICLE", 22, 0.012)
t = add_visit("dubai_hotel", t, 3100)
t = add_activity("dubai_hotel", "dxb", t, 40, "IN_PASSENGER_VEHICLE", 22, 0.012)
t = add_visit("dxb", t, 140)
t = add_activity("dxb", "lhr", t, 445, "FLYING", 55, 0.0)
t = add_visit("lhr", t, 75)
t = add_activity("lhr", "london", t, 62, "IN_SUBWAY", 30, 0.015)
t = add_visit("london", t, 2000)
t = add_activity("london", "paris", t, 155, "IN_TRAIN", 60, 0.020)
t = add_visit("paris", t, 2800)
t = add_activity("paris", "london", t, 150, "IN_TRAIN", 60, 0.020)
t = add_visit("london", t, 1500)
t = add_activity("london", "lhr", t, 58, "IN_SUBWAY", 30, 0.015)
t = add_visit("lhr", t, 120)
t = add_activity("lhr", "maa_airport", t, 620, "FLYING", 70, 0.0)
t = add_visit("home", t, 1400)

# --- Singapore ---
t = datetime(2025, 8, 19, 3, 0, tzinfo=IST)
t = add_activity("home", "maa_airport", t, 33, "IN_PASSENGER_VEHICLE", 18, 0.006)
t = add_visit("maa_airport", t, 110)
t = add_activity("maa_airport", "sin", t, 275, "FLYING", 42, 0.0)
t = add_visit("sin", t, 70)
t = add_activity("sin", "singapore", t, 30, "IN_SUBWAY", 20, 0.010)
t = add_visit("singapore", t, 4200)
t = add_activity("singapore", "sin", t, 32, "IN_SUBWAY", 20, 0.010)
t = add_activity("sin", "maa_airport", t, 280, "FLYING", 42, 0.0)
t = add_visit("home", t, 1000)

segments.sort(key=lambda s: s["startTime"])

doc = {
    "semanticSegments": segments,
    "rawSignals": [],
    "userLocationProfile": {
        "frequentPlaces": [
            {
                "placeId": PLACES["home"][3],
                "placeLocation": fmt_latlng(*PLACES["home"][:2]),
                "label": "HOME",
            },
            {
                "placeId": PLACES["office"][3],
                "placeLocation": fmt_latlng(*PLACES["office"][:2]),
                "label": "WORK",
            },
        ]
    },
}

out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "data", "Timeline.sample.json")
with open(out, "w") as f:
    json.dump(doc, f, indent=1)

visits = sum(1 for s in segments if "visit" in s)
acts = sum(1 for s in segments if "activity" in s)
crumbs = sum(len(s.get("timelinePath", [])) for s in segments)
print(f"wrote {out}")
print(f"  segments      {len(segments)}")
print(f"  visits        {visits}")
print(f"  activities    {acts}")
print(f"  breadcrumbs   {crumbs}")
print(f"  range         {segments[0]['startTime'][:10]} .. {segments[-1]['endTime'][:10]}")
