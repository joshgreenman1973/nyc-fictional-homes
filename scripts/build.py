#!/usr/bin/env python3
"""Merge the research files, geocode each home and check it lands in the right borough.

Inputs:  research/raw/*.json  (records in the schema described in research/BRIEF.md)
         research/overrides.json  (optional hand corrections keyed by record id)
Outputs: data/homes.json          (what the page loads)
         research/qa_report.md    (every problem the checks found)

Geocoders, both free and keyless:
  1. NYC Planning Labs GeoSearch (addresses)       geosearch.planninglabs.nyc
  2. OpenStreetMap Nominatim (corners, landmarks)  nominatim.openstreetmap.org, 1 request/second
Results are cached in data/geocode_cache.json so a rebuild costs nothing.
"""
import json, glob, os, re, sys, time, hashlib
import requests
from shapely.geometry import shape, Point

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "research", "raw")
CACHE_P = os.path.join(ROOT, "data", "geocode_cache.json")
OVR_P = os.path.join(ROOT, "research", "overrides.json")
OUT_P = os.path.join(ROOT, "data", "homes.json")
QA_P = os.path.join(ROOT, "research", "qa_report.md")
UA = {"User-Agent": "nyc-fiction-homes-build/1.0 (static map build script)"}

MEDIA = {"book", "film", "tv", "theater", "comics"}
PRECISION = ["address_in_work", "building_in_work", "creator_stated", "screen_exterior",
             "block_inferred", "neighborhood", "invented"]
BOROUGHS = {"Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"}

cache = json.load(open(CACHE_P)) if os.path.exists(CACHE_P) else {}
overrides = json.load(open(OVR_P)) if os.path.exists(OVR_P) else {}
QC_P = os.path.join(ROOT, "research", "quote_check.json")
qcheck = json.load(open(QC_P)) if os.path.exists(QC_P) else {}
# Batches whose researchers matched quotes only through a summarizing fetch tool. If our own
# download of the page fails, their quotes cannot be trusted; the other batches checked
# their quotes against raw page text themselves.
RAW_TEXT_UNCHECKED = {"tv", "books_1960_now", "gaps_screen", "gaps_books_theater"}
boro_shapes = {f["properties"]["BoroName"]: shape(f["geometry"])
               for f in json.load(open(os.path.join(ROOT, "data", "boroughs_raw.geojson")))["features"]}
_last_nom = [0.0]


def norm_boro(b):
    if not b:
        return None
    b = b.strip()
    if b.lower().startswith("the bronx"):
        return "Bronx"
    return b


def which_boro(lat, lon):
    p = Point(lon, lat)
    for name, g in boro_shapes.items():
        if g.contains(p):
            return name
    # coastline points (piers, islands) can fall just outside the polygon
    best = min(boro_shapes.items(), key=lambda kv: kv[1].distance(p))
    return best[0] + ("" if best[1].distance(p) < 0.004 else " (offshore)")


def geosearch(q, boro=None):
    num = re.match(r"\s*(\d+[A-Za-z]?(?:-\d+)?)\s", q)
    if not num:
        return None  # GeoSearch is an address matcher; corners and names go elsewhere
    r = requests.get("https://geosearch.planninglabs.nyc/v2/search",
                     params={"text": q, "size": 5}, headers=UA, timeout=20)
    for f in r.json().get("features", []):
        pr = f["properties"]
        # Trust GeoSearch only when the house number AND the borough are the ones we asked for.
        if not pr.get("label", "").upper().startswith(num.group(1).upper()):
            continue
        if boro and pr.get("borough") and pr["borough"] != boro:
            continue
        # East and West streets share numbers; the matcher must keep the direction we asked for.
        want = re.search(r"\b(east|west|e\.|w\.|e|w)\s+\d", q, re.I)
        if want:
            wd = "EAST" if want.group(1).lower().startswith("e") else "WEST"
            if not re.search(rf"\b{wd}\b", pr.get("label", "").upper()):
                continue
        lon, lat = f["geometry"]["coordinates"]
        return {"lat": lat, "lon": lon, "label": pr.get("label"), "via": "geosearch"}
    return None


ORD = {"first": "1st", "second": "2nd", "third": "3rd", "fourth": "4th", "fifth": "5th", "sixth": "6th",
       "seventh": "7th", "eighth": "8th", "ninth": "9th", "tenth": "10th", "eleventh": "11th", "twelfth": "12th"}
ABBR = {"st": "street", "st.": "street", "ave": "avenue", "ave.": "avenue", "av": "avenue", "blvd": "boulevard",
        "pl": "place", "pl.": "place", "rd": "road", "dr": "drive", "pkwy": "parkway", "e": "east", "e.": "east",
        "w": "west", "w.": "west", "n": "north", "s": "south", "sq": "square"}
ALIAS = {"lenox avenue": ["lenox avenue", "malcolm x boulevard"],
         "sixth avenue": ["6th avenue", "avenue of the americas"], "6th avenue": ["6th avenue", "avenue of the americas"],
         "seventh avenue south": ["7th avenue south"], "central park west": ["central park west"]}
OVERPASS = ["https://maps.mail.ru/osm/tools/overpass/api/interpreter", "https://overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter"]


def street_regex(name):
    low = re.sub(r"^(st\.?|saint)\s+(?=marks?\b)", "saint ", name.lower().strip())
    words = [ABBR.get(w, w) for w in low.replace(",", " ").split()]
    base = " ".join(words)
    variants = ALIAS.get(base, [base])
    out = []
    for v in variants:
        toks = []
        for w in v.split():
            if w in ORD:
                toks.append(f"({w}|{ORD[w]})")
            elif re.fullmatch(r"\d+(st|nd|rd|th)", w):
                word = [k for k, val in ORD.items() if val == w]
                toks.append(f"({w}|{word[0]})" if word else w)
            else:
                toks.append(re.escape(w))
        alt = " ".join(toks)
        if re.match(r"^\(?\d", alt):  # "31st Street" with no East or West: allow either
            alt = "((east|west) )?" + alt
        if alt.startswith("saint"):
            alt = "(saint|st\\.?) " + alt[len("saint "):]
        out.append(alt)
    return "^(" + "|".join(out) + ")$"


_streets = {}


def street_index():
    """name -> set of node ids, and node id -> (lat, lon), from data/osm_streets.json
    (named NYC streets from OpenStreetMap, fetched once by borough through Overpass)."""
    if not _streets:
        names, nodes = {}, {}
        for e in json.load(open(os.path.join(ROOT, "data", "osm_streets.json")))["elements"]:
            if e["type"] == "node":
                nodes[e["id"]] = (e["lat"], e["lon"])
            elif e["type"] == "way":
                t = e.get("tags", {})
                for k in ("name", "alt_name", "old_name", "official_name"):
                    for nm in (t.get(k) or "").split(";"):
                        if nm.strip():
                            names.setdefault(nm.strip().lower(), set()).update(e.get("nodes", []))
        _streets.update(names=names, nodes=nodes)
    return _streets


def intersection(q, boro):
    m = re.match(r"\s*(.+?)\s+(?:&|and|at)\s+(.+?)(?:,\s*(Manhattan|Brooklyn|Queens|Bronx|The Bronx|Staten Island|New York).*)?$", q, re.I)
    if not m or not boro or boro not in boro_shapes:
        return None
    a, b = m.group(1), m.group(2)
    idx = street_index()
    def nodes_for(street):
        rx = re.compile(street_regex(street), re.I)
        out = set()
        for nm, ns in idx["names"].items():
            if rx.match(nm):
                out |= ns
        return out
    common = nodes_for(a) & nodes_for(b)
    pts = [idx["nodes"][i] for i in common if i in idx["nodes"]]
    pts = [p for p in pts if boro_shapes[boro].buffer(0.002).contains(Point(p[1], p[0]))]
    if not pts:
        return None
    pts.sort()
    lat, lon = pts[len(pts) // 2]  # the median node: divided avenues meet a street at two or more nodes
    return {"lat": lat, "lon": lon, "label": f"{a} and {b} (OpenStreetMap)", "via": "osm-corner"}


def nominatim(q):
    """OpenStreetMap search, for named buildings and places. One request a second, per its policy."""
    wait = 1.1 - (time.time() - _last_nom[0])
    if wait > 0:
        time.sleep(wait)
    _last_nom[0] = time.time()
    qq = q if "new york" in q.lower() else q + ", New York City"
    r = requests.get("https://nominatim.openstreetmap.org/search",
                     params={"q": qq, "format": "jsonv2", "limit": 1,
                             "viewbox": "-74.26,40.92,-73.69,40.49", "bounded": 1},
                     headers=UA, timeout=15)
    js = r.json()
    if not js:
        return None
    j = js[0]
    return {"lat": float(j["lat"]), "lon": float(j["lon"]), "label": j.get("display_name"), "via": "nominatim"}


def geocode(q, boro=None):
    ck = f"{q}|{boro}"
    if ck in cache:
        return cache[ck]
    res = None
    try:
        res = geosearch(q, boro)
    except Exception as e:  # network hiccup: fall through
        print("geosearch error", q, e, file=sys.stderr)
    if res is None and re.search(r"\s(&|and|at)\s", q):
        try:
            res = intersection(q, boro)
        except Exception as e:
            print("overpass error", q, e, file=sys.stderr)
    if res is None:
        # Nominatim does better with "X Street & Y Avenue" written as "X Street and Y Avenue"
        try:
            res = nominatim(q.replace("&", "and"))
        except Exception as e:
            print("nominatim error", q, e, file=sys.stderr)
    if res and boro and res["via"] == "nominatim" and which_boro(res["lat"], res["lon"]) != boro:
        res = None  # landed in the wrong borough; leave it for a hand fix
    if res is not None:
        cache[ck] = res
        json.dump(cache, open(CACHE_P, "w"), indent=1)
    return res


def rid(r):
    base = f"{r.get('home_key','')}|{r.get('kind','story')}|{r.get('work','')}"
    return hashlib.sha1(base.encode()).hexdigest()[:10]


def destack(out, problems):
    """Hand-placed neighborhood marks often share one centroid, which stacks unrelated homes on a
    single dot. Fan the extras out in a ring around it (a few hundred meters, well inside their
    circles), keeping the first where it was. Exact addresses are never moved."""
    import math
    groups = {}
    for r in out:
        if r["lat"] is None or r["placed_by"] != "approx":
            continue
        groups.setdefault((round(r["lat"], 4), round(r["lon"], 4)), []).append(r)
    moved = 0
    for g in groups.values():
        keys = []
        for r in g:
            if r["home_key"] not in keys:
                keys.append(r["home_key"])
        if len(keys) < 2:
            continue
        keys.sort()
        for n, k in enumerate(keys[1:], 1):
            ang = 2 * math.pi * (n - 1) / (len(keys) - 1) + 0.6
            dist = min(260, 0.5 * min((r["radius_m"] or 400) for r in g if r["home_key"] == k))
            for r in g:
                if r["home_key"] == k:
                    r["lat"] = round(r["lat"] + dist * math.cos(ang) / 111320, 6)
                    r["lon"] = round(r["lon"] + dist * math.sin(ang) / (111320 * math.cos(math.radians(r["lat"]))), 6)
                    moved += 1
    if moved:
        problems.append(f"- note: {moved} hand-placed marks that shared a point with another home were fanned out")


def main():
    problems, out, seen, seen_addr = [], [], set(), {}
    for path in sorted(glob.glob(os.path.join(RAW, "*.json"))):
        batch = os.path.basename(path)[:-5]
        try:
            recs = json.load(open(path))
        except Exception as e:
            problems.append(f"- **{batch}**: file does not parse ({e})")
            continue
        for r in recs:
            r = dict(r)
            i = rid(r)
            if i in seen and r.get("kind") == "exterior" and seen_addr.get(i) != (r.get("address_as_given") or ""):
                # same home and kind but another building (a show that changed exteriors): keep it
                i = hashlib.sha1(f"{i}|{r.get('address_as_given') or ''}".encode()).hexdigest()[:10]
            seen_addr.setdefault(i, r.get("address_as_given") or "")
            if i in seen:
                problems.append(f"- duplicate record dropped: {r.get('character')} / {r.get('work')} ({batch})")
                continue
            seen.add(i)
            ov = dict(overrides.get(i, {}))
            if ov.get("notes_append"):
                r["notes"] = ((r.get("notes") or "") + " " + ov.pop("notes_append")).strip()
            r.update(ov)
            if r.get("drop"):
                continue
            who = f"{r.get('character')} — {r.get('work')} [{i}, {batch}]"
            r["borough"] = norm_boro(r.get("borough"))
            bad = []
            if r.get("medium") not in MEDIA: bad.append(f"medium {r.get('medium')!r}")
            if r.get("precision") not in PRECISION: bad.append(f"precision {r.get('precision')!r}")
            if not r.get("source_url") or not r.get("source_quote"): bad.append("missing source or quote")
            if r.get("borough") not in BOROUGHS and not r.get("exterior_outside_nyc"):
                bad.append(f"borough {r.get('borough')!r}")
            if bad:
                problems.append(f"- dropped {who}: " + ", ".join(bad))
                continue

            lat = lon = label = via = None
            if r.get("exterior_outside_nyc"):
                pass
            elif r.get("geocode_query"):
                g = geocode(r["geocode_query"], r["borough"])
                if g:
                    lat, lon, label, via = g["lat"], g["lon"], g["label"], g["via"]
            if lat is None and r.get("approx_lat") and not r.get("exterior_outside_nyc"):
                lat, lon, label, via = r["approx_lat"], r["approx_lon"], "placed by hand", "approx"
            if lat is None and not r.get("exterior_outside_nyc"):
                problems.append(f"- not placed {who}: query {r.get('geocode_query')!r}")
                continue
            if lat is not None:
                got = which_boro(lat, lon)
                if got != r["borough"]:
                    problems.append(f"- borough mismatch {who}: says {r['borough']}, point is in {got} "
                                    f"(query {r.get('geocode_query')!r} → {label})")
            ss, se = r.get("setting_start"), r.get("setting_end")
            if ss is None and se is None:
                problems.append(f"- no setting years {who}; using work year")
                ss = se = r.get("work_year")
            ss = ss if ss is not None else se
            se = se if se is not None else ss
            srcs = []
            for u, q in ((r.get("source_url"), r.get("source_quote")), (r.get("source2_url"), r.get("source2_quote"))):
                if not (u and q):
                    continue
                chk = qcheck.get(f"{u}||{q}", {"status": "unchecked"})
                st = chk["status"]
                if st == "replaced":
                    q = chk["quote"]
                elif st == "failed" or (st == "unreachable" and batch in RAW_TEXT_UNCHECKED):
                    problems.append(f"- source dropped ({st}) {who}: {u}")
                    continue
                srcs.append({"url": u, "quote": q, "check": st})
            if not srcs:
                problems.append(f"- dropped {who}: no source survived the quote check")
                continue
            out.append({
                "id": i, "home_key": r.get("home_key"), "kind": r.get("kind", "story"),
                "character": r.get("character"), "household": r.get("household"),
                "work": r.get("work"), "medium": r["medium"], "creator": r.get("creator"),
                "work_year": r.get("work_year"), "start": ss, "end": se,
                "address": r.get("address_as_given"), "borough": r.get("borough"),
                "neighborhood": r.get("neighborhood"), "precision": r["precision"],
                "lat": round(lat, 6) if lat is not None else None,
                "lon": round(lon, 6) if lon is not None else None,
                "radius_m": r.get("radius_m") or 0, "placed_by": via, "geocode_label": label,
                "outside_nyc": bool(r.get("exterior_outside_nyc")),
                "notes": r.get("notes"), "sources": srcs, "batch": batch,
            })
    json.dump(cache, open(CACHE_P, "w"), indent=1)
    destack(out, problems)
    out.sort(key=lambda x: (x["start"] or 0, x["character"] or ""))
    json.dump(out, open(OUT_P, "w"), ensure_ascii=False, indent=1)
    with open(QA_P, "w") as f:
        f.write(f"# QA report\n\n{len(out)} records kept. {len(problems)} problems.\n\n")
        f.write("\n".join(problems) + "\n")
    print(f"{len(out)} records, {len(problems)} problems → {QA_P}")


if __name__ == "__main__":
    main()
