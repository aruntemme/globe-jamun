"""Build the test fixtures under web/_t/ (gitignored).

The 13-place sample is far too small to expose the problems that actually bite:
geometry rebuilds, draw-call counts and error paths only show up at real sizes
or on shapes the sample never produces. Regenerate with:

    python3 tools/make-fixtures.py

then load each through the page and check for uncaught errors.
"""
import copy
import json
import os
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "web", "_t")
os.makedirs(OUT, exist_ok=True)
segs = json.load(open(os.path.join(ROOT, "data", "Timeline.sample.json")))["semanticSegments"]


def write(name, obj):
    path = os.path.join(OUT, name + ".json")
    with open(path, "w") as fh:
        json.dump(obj, fh)
    print(f"  {name:<16} {os.path.getsize(path) / 1e6:8.2f} MB")


# Android baseline
write("android", {"semanticSegments": segs})

# iOS: bare array, geo: URIs, placeID, distances as strings
ios = lambda t: "geo:" + t.replace("°", "").replace(", ", ",")
arr = []
for seg in segs:
    s = copy.deepcopy(seg)
    if "visit" in s:
        tc = s["visit"]["topCandidate"]
        tc["placeID"] = tc.pop("placeId")
        tc["placeLocation"] = ios(tc["placeLocation"]["latLng"])
    if "activity" in s:
        a = s["activity"]
        a["start"], a["end"] = ios(a["start"]["latLng"]), ios(a["end"]["latLng"])
        a["distanceMeters"] = str(a["distanceMeters"])
    for p in s.get("timelinePath", []):
        p["point"] = ios(p["point"])
    arr.append(s)
write("ios", arr)

# Three years of it — the size that exposes performance problems
big = []
for week in range(52 * 3):
    shift = timedelta(weeks=week)
    for seg in segs:
        s = copy.deepcopy(seg)
        for k in ("startTime", "endTime"):
            if k in s:
                s[k] = (datetime.fromisoformat(s[k]) + shift).isoformat()
        big.append(s)
big.sort(key=lambda s: s["startTime"])
write("big", {"semanticSegments": big})

# Every journey lacking breadcrumbs, so all geometry is synthesised
write("nobreadcrumbs", {"semanticSegments":
                        [{k: v for k, v in copy.deepcopy(s).items() if k != "timelinePath"}
                         for s in segs]})

# Visits but no journeys: travel must refuse to start
write("visitsonly", {"semanticSegments": [copy.deepcopy(s) for s in segs if "visit" in s]})

# Routes crossing the antimeridian
ll = lambda lat, lng: {"latLng": f"{lat:.6f}°, {lng:.6f}°"}
places = [("sg", 1.3521, 103.8198), ("hnl", 21.3069, -157.8583), ("nrt", 35.6762, 139.6503)]
am, t = [], datetime(2025, 6, 1, 8, 0)
for i, a in enumerate(places):
    b = places[(i + 1) % len(places)]
    am.append({"startTime": t.isoformat() + "+00:00", "endTime": (t + timedelta(hours=2)).isoformat() + "+00:00",
               "visit": {"hierarchyLevel": 0, "probability": 0.9,
                         "topCandidate": {"placeId": f"p_{a[0]}", "semanticType": "UNKNOWN",
                                          "probability": 0.9, "placeLocation": ll(a[1], a[2])}}})
    t += timedelta(hours=3)
    am.append({"startTime": t.isoformat() + "+00:00", "endTime": (t + timedelta(hours=10)).isoformat() + "+00:00",
               "activity": {"start": ll(a[1], a[2]), "end": ll(b[1], b[2]), "distanceMeters": 9000000,
                            "topCandidate": {"type": "FLYING", "probability": 0.95}}})
    t += timedelta(hours=12)
write("antimeridian", {"semanticSegments": am})

# Error paths
with open(os.path.join(OUT, "malformed.json"), "w") as fh:
    fh.write('{"semanticSegments": [ {"startTime": "2025-01-01T00:00:00Z" ')
print(f"  {'malformed':<16} {os.path.getsize(os.path.join(OUT, 'malformed.json')) / 1e6:8.2f} MB")
write("empty", {"semanticSegments": []})
