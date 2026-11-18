#!/usr/bin/env python3
"""Download named NYC streets from OpenStreetMap (via Overpass) into data/osm_streets.json.
build.py uses it to place street corners ("East 11th Street and Avenue B") offline.
Fetched in borough slices because a single citywide query times out."""
import json, os, time, requests
from shapely.geometry import shape
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EP = ["https://maps.mail.ru/osm/tools/overpass/api/interpreter", "https://overpass-api.de/api/interpreter"]
b = {f["properties"]["BoroName"]: shape(f["geometry"]).bounds
     for f in json.load(open(os.path.join(ROOT, "data", "boroughs_raw.geojson")))["features"]}
els = []
os.makedirs(os.path.join(ROOT, "data", "osm_slices"), exist_ok=True)
for name, (minx, miny, maxx, maxy) in b.items():
    for k in range(3):
        y0, y1 = miny + (maxy - miny) * k / 3, miny + (maxy - miny) * (k + 1) / 3
        q = (f'[out:json][timeout:170];way["highway"~"^(trunk|primary|secondary|tertiary|residential|unclassified|'
             f'living_street|pedestrian)$"]["name"]({y0:.4f},{minx:.4f},{y1:.4f},{maxx:.4f});out body;>;out skel qt;')
        sp = os.path.join(ROOT, "data", "osm_slices", f"{name}_{k}.json")
        if os.path.exists(sp):
            els += json.load(open(sp)); continue
        for attempt in range(20):
            try:
                r = requests.post(EP[attempt % 2], data={"data": q}, headers={"User-Agent": "nyc-fiction-homes-build/1.0"}, timeout=200)
                got = r.json()["elements"]; els += got; json.dump(got, open(sp, "w")); print(name, k, len(got)); break
            except Exception as e:
                print(name, k, "retry", str(e)[:60]); time.sleep(15)
        else:
            raise SystemExit(f"could not fetch {name} slice {k}")
json.dump({"elements": els}, open(os.path.join(ROOT, "data", "osm_streets.json"), "w"))
