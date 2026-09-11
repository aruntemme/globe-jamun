"""Build an offline city lookup from the GeoNames dump.

Place names have to be resolved without a network call: reverse geocoding your
visits through Nominatim would send your home coordinates to a third party,
which is exactly what this project promises not to do. So the names ship with
the app and the lookup happens in your browser.

Source: https://download.geonames.org/export/dump/  (CC BY 4.0)
"""
import io
import json
import os
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DUMP = "cities15000"          # populated places with more than 15k people
URL = f"https://download.geonames.org/export/dump/{DUMP}.zip"

print(f"downloading {URL} …")
raw = urllib.request.urlopen(URL, timeout=120).read()
with zipfile.ZipFile(io.BytesIO(raw)) as z:
    text = z.read(f"{DUMP}.txt").decode("utf-8")

cities = []
for line in text.splitlines():
    f = line.split("\t")
    if len(f) < 15:
        continue
    name, lat, lng, cc, pop = f[1], f[4], f[5], f[8], f[14]
    try:
        lat, lng, pop = float(lat), float(lng), int(pop or 0)
    except ValueError:
        continue
    cities.append([name, cc, round(lat, 4), round(lng, 4), pop])

# Biggest first: ties at the same distance should resolve to the better-known place.
cities.sort(key=lambda c: -c[4])

out = os.path.join(ROOT, "web", "cities.json")
with open(out, "w", encoding="utf-8") as fh:
    json.dump({"source": "GeoNames " + DUMP + " (CC BY 4.0)", "cities": cities},
              fh, ensure_ascii=False, separators=(",", ":"))

size = os.path.getsize(out)
print(f"wrote {out}")
print(f"  cities   {len(cities):,}")
print(f"  size     {size/1e6:.2f} MB raw")
