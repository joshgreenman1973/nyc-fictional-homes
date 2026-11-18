#!/usr/bin/env python3
"""Find pictures and links for each work and each building. Run after build.py.

Works:
  film, tv          -> TMDB backdrop (a promotional still) and poster. Key: TMDB_API_KEY env var
                       (the same key as movie-time-machine/.env). Images are keyless image.tmdb.org URLs.
  book, theater,
  comics            -> the lead image of the work's Wikipedia article (usually a cover or poster).
  all               -> a link to the work's Wikipedia article when one is found.
Buildings (only for marks precise enough to stand at a real building):
  1. a Wikipedia article about a building within 40 meters of the point, with its lead image
  2. otherwise a Wikimedia Commons photo within 60 meters whose file name names the same street
     (the street test keeps out the parked cars and passing parades that geotag nearby)
Output: data/media.json {"works": {work_key: {...}}, "venues": {record_id: {...}}}
"""
import json, os, re, sys, time, unicodedata
from concurrent.futures import ThreadPoolExecutor
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOMES = json.load(open(os.path.join(ROOT, "data", "homes.json")))
OUT_P = os.path.join(ROOT, "data", "media.json")
UA = {"User-Agent": "nyc-fiction-homes-build/1.0 (static map build script)"}
KEY = os.environ.get("TMDB_API_KEY")
prev = json.load(open(OUT_P)) if os.path.exists(OUT_P) else {"works": {}, "venues": {}}
SKIP_WORDS = re.compile(r"\b(car|sedan|suv|truck|bus|taxi|cab|parade|protest|march|bike|bicycle|dog|cat|portrait|selfie|logo|map|diagram|food|sign)\b", re.I)


def n(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"^(the|a|an)\s+", "", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def work_key(r):
    return f"{r['work']}|{r['medium']}"


def get(url, **params):
    if "wiki" in url:
        time.sleep(0.4)
    for i in range(6):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=25)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(6 * (i + 1)); continue
            return r.json()
        except Exception:
            time.sleep(1.5)
    return {}


def wiki_image(js):
    """Wikimedia serves only some thumbnail widths and none wider than the file, so pick from the
    summary's own size data: a 500px thumbnail when the original is wider, else the original."""
    o, t = js.get("originalimage") or {}, js.get("thumbnail") or {}
    if not o.get("source"):
        return None
    src = o["source"].split("?")[0]
    if (o.get("width") or 0) > 500 and t.get("source") and "/thumb/" in t["source"]:
        return re.sub(r"/\d+px-", "/500px-", t["source"].split("?")[0]).replace("thumb.wikimedia.org", "upload.wikimedia.org")
    return src


def wiki_summary(title):
    js = get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{title.replace(' ', '_')}")
    if not js or js.get("type") == "disambiguation" or "title" not in js:
        return None
    return {"title": js["title"], "url": js["content_urls"]["desktop"]["page"], "img": wiki_image(js),
            "desc": js.get("description")}


SUFFIX = {"book": ["novel", "novella", "short story", "book"], "theater": ["play", "musical", "opera"],
          "comics": ["comics", "comic strip", "comic book"], "film": ["film"], "tv": ["TV series", "American TV series"]}


def find_wiki(work, medium, creator, year, hint_urls):
    wn = n(work)
    for u in hint_urls:  # a research source that is already the work's own article
        if "wikipedia.org/wiki/" in u:
            t = u.split("/wiki/", 1)[1].split("#")[0].replace("_", " ")
            if n(re.sub(r"\s*\(.*\)$", "", requests.utils.unquote(t))) == wn:
                s = wiki_summary(requests.utils.unquote(t))
                if s: return s
    cands = [f"{work} ({year} {sfx})" for sfx in SUFFIX[medium]] + [f"{work} ({sfx})" for sfx in SUFFIX[medium]] + [work]
    for c in cands:
        s = wiki_summary(c)
        if s and n(re.sub(r"\s*\(.*\)$", "", s["title"])) == wn:
            d = (s.get("desc") or "").lower()
            if c == work and medium in ("book", "theater") and not any(w in d for w in ["novel", "play", "musical", "story", "book", "opera", "comic", "film", "series", "sitcom", "drama"]):
                continue  # bare title landed on something else
            return s
    js = get("https://en.wikipedia.org/w/api.php", action="query", list="search", format="json", srlimit=3,
             srsearch=f'"{work}" {creator or ""} {SUFFIX[medium][0]}')
    for hit in js.get("query", {}).get("search", []):
        if n(re.sub(r"\s*\(.*\)$", "", hit["title"])) == wn:
            return wiki_summary(hit["title"])
    return None


def tmdb(work, medium, year):
    if not KEY: return None
    kind = "movie" if medium == "film" else "tv"
    yk = "year" if kind == "movie" else "first_air_date_year"
    for params in ({yk: year}, {}):
        js = get(f"https://api.themoviedb.org/3/search/{kind}", api_key=KEY, query=work, **params)
        for r in js.get("results", [])[:5]:
            t = r.get("title") or r.get("name") or ""
            if n(t) == n(work) and (r.get("backdrop_path") or r.get("poster_path")):
                return {"tmdb_id": r["id"], "kind": kind,
                        "backdrop": f"https://image.tmdb.org/t/p/w780{r['backdrop_path']}" if r.get("backdrop_path") else None,
                        "poster": f"https://image.tmdb.org/t/p/w342{r['poster_path']}" if r.get("poster_path") else None,
                        "link": f"https://www.themoviedb.org/{kind}/{r['id']}"}
    return None


def enrich_work(item):
    k, r, hints = item
    old = prev["works"].get(k)
    if old is not None:
        old = dict(old)
        if "640px-" in (old.get("wiki_img") or ""):
            old.pop("wiki_img")
        if old.get("wiki") and not old.get("wiki_img"):
            s = wiki_summary(requests.utils.unquote(old["wiki"].split("/wiki/", 1)[1]))
            if s and s.get("img"):
                old["wiki_img"] = s["img"]
        return k, old
    out = {}
    w = find_wiki(r["work"], r["medium"], r.get("creator"), r.get("work_year"), hints)
    if w:
        out["wiki"] = w["url"]
        if w.get("img"):
            out["wiki_img"] = w["img"]
    if r["medium"] in ("film", "tv"):
        t = tmdb(r["work"], r["medium"], r.get("work_year"))
        if t:
            out.update({"still": t["backdrop"], "poster": t["poster"], "tmdb": t["link"]})
    return k, out


VENUE_TITLES = {k: v for k, v in json.load(open(os.path.join(ROOT, "research", "venue_titles.json"))).items()
                if not k.startswith("_")}
BAD_VENUES = {"Dumbo, Brooklyn"}
GENERIC = {"new", "york", "city", "building", "house", "hotel", "apartment", "apartments", "manhattan", "brooklyn",
           "queens", "bronx", "the", "from", "front", "view", "facade", "east", "west", "north", "south", "closeup",
           "panorama", "file", "jpg", "png"}
STREETY = re.compile(r"\b(street|st|avenue|ave|av|square|road|place|drive|broadway|boulevard|lane|plaza|park)\b", re.I)


def street_words(addr):
    stop = {"street", "avenue", "place", "road", "drive", "east", "west", "north", "south", "york", "manhattan",
            "brooklyn", "queens", "bronx", "staten", "island", "near", "corner", "between", "with", "from", "where"}
    return {w.lower() for w in re.findall(r"[A-Za-z]{4,}", addr) if w.lower() not in stop}


def fits(title, r):
    """Does a photo or article title name this home's own building, not a neighbor or the street?"""
    addr = r.get("address") or ""
    t = n(title.replace("File:", "").rsplit(".", 1)[0])
    anums = set(re.findall(r"\b(\d{1,5})\b", n(addr)))
    tnums = {x for x in re.findall(r"\b(\d{1,5})\b", t) if not re.fullmatch(r"(18|19|20)\d\d", x)}
    if anums & tnums and any(w in t for w in street_words(addr)):
        return True  # house number and street both in the title
    bare = re.sub(r"\(.*?\)", "", title.replace("File:", "").rsplit(".", 1)[0])
    if tnums or STREETY.search(bare):
        return False
    tt = [w for w in n(bare).split() if len(w) > 3 and w not in GENERIC]
    return bool(tt) and all(w in n(addr) for w in tt)  # the building's own name


def enrich_venue(r):
    old = prev["venues"].get(r["id"])
    if old and old.get("src") and "640px-" not in old["src"] and old.get("title") not in BAD_VENUES:
        return r["id"], old
    if r["id"] in VENUE_TITLES:
        s = wiki_summary(VENUE_TITLES[r["id"]])
        if s and s.get("img"):
            return r["id"], {"src": s["img"], "title": s["title"], "link": s["url"], "credit": "Wikipedia"}
        return r["id"], None
    ll = f"{r['lat']}|{r['lon']}"
    js = get("https://en.wikipedia.org/w/api.php", action="query", list="geosearch", gscoord=ll, gsradius=50,
             gslimit=10, format="json")
    for hit in js.get("query", {}).get("geosearch", []):
        if not fits(hit["title"], r):
            continue
        s = wiki_summary(hit["title"])
        if s and s.get("img") and not re.search(r"(neighborhood|neighbourhood|district|borough|station|park|street|avenue)", (s.get("desc") or "").lower()):
            return r["id"], {"src": s["img"], "title": s["title"], "link": s["url"], "credit": "Wikipedia"}
    js = get("https://commons.wikimedia.org/w/api.php", action="query", list="geosearch", gscoord=ll, gsradius=60,
             gsnamespace=6, gslimit=50, format="json")
    for hit in js.get("query", {}).get("geosearch", []):
        t = hit["title"]
        if SKIP_WORDS.search(t) or not fits(t, r):
            continue
        info = get("https://commons.wikimedia.org/w/api.php", action="query", titles=t, prop="imageinfo",
                   iiprop="url|extmetadata", iiurlwidth=500, format="json")
        pg = next(iter(info.get("query", {}).get("pages", {}).values()), {})
        ii = (pg.get("imageinfo") or [{}])[0]
        if not ii.get("thumburl"):
            continue
        md = ii.get("extmetadata", {})
        artist = re.sub(r"<[^>]+>", "", (md.get("Artist") or {}).get("value", "")).strip()
        lic = (md.get("LicenseShortName") or {}).get("value", "")
        return r["id"], {"src": ii["thumburl"], "title": t.replace("File:", "").rsplit(".", 1)[0],
                         "link": ii.get("descriptionurl"),
                         "credit": ", ".join(x for x in [artist, lic] if x) + " via Wikimedia Commons"}
    return r["id"], None


_ok = {}


def loads(u):
    if u not in _ok:
        try:
            _ok[u] = requests.head(u, headers=UA, timeout=20, allow_redirects=True).status_code == 200
        except Exception:
            _ok[u] = False
        time.sleep(0.15)
    return _ok[u]


def sized(url):
    """Wikimedia serves only some thumbnail widths, and none wider than the original file.
    Return the widest of 500/330/250 that loads, else the original file."""
    if not url or "wikimedia.org" not in url:
        return url
    u = url.split("?")[0].replace("thumb.wikimedia.org", "upload.wikimedia.org")
    if "/thumb/" not in u or not re.search(r"/\d+px-", u):
        return u if loads(u) else None
    for w in (500, 330, 250):
        c = re.sub(r"/\d+px-", f"/{w}px-", u)
        if loads(c):
            return c
    orig = u.replace("/thumb/", "/").rsplit("/", 1)[0]
    return orig if loads(orig) else None


def fix_sizes(W, V):
    for w in W.values():
        if w.get("wiki_img"):
            w["wiki_img"] = sized(w["wiki_img"])
            if not w["wiki_img"]:
                del w["wiki_img"]
    for k in list(V):
        V[k]["src"] = sized(V[k]["src"])
        if not V[k]["src"]:
            del V[k]


def main():
    works = {}
    for r in HOMES:
        k = work_key(r)
        works.setdefault(k, [r, []])
        works[k][1] += [s["url"] for s in r["sources"]]
    with ThreadPoolExecutor(1) as ex:
        W = dict(ex.map(enrich_work, [(k, v[0], v[1]) for k, v in works.items()]))
    precise = [r for r in HOMES if r["lat"] is not None and r["precision"] in
               ("address_in_work", "building_in_work", "creator_stated", "screen_exterior")]
    with ThreadPoolExecutor(1) as ex:
        V = {k: v for k, v in ex.map(enrich_venue, precise) if v}
    json.dump({"works": W, "venues": V}, open(OUT_P, "w"), ensure_ascii=False, indent=1)
    print(f"works {len(W)} ({sum(1 for v in W.values() if v.get('still') or v.get('wiki_img'))} with a picture), "
          f"venues {len(V)} of {len(precise)} precise marks")


if __name__ == "__main__":
    main()
