#!/usr/bin/env python3
"""Check every source quotation against the text of its source page.

Some research batches fetched pages through a summarizing tool, so a quote can be a
paraphrase. This script downloads each source page itself and, for every record's quote:
  verified  - the quote appears in the page text (allowing for ellipses and typography)
  replaced  - it does not, but one sentence on the page clearly carries the same words;
              that real sentence replaces the paraphrase
  failed    - neither; build.py drops that source, and drops the record if no source is left
  unreachable - the page could not be downloaded; treated like failed

Pages are cached in research/pages/ so reruns are free.
Output: research/quote_check.json  {"<url>||<quote>": {"status":..., "quote":...}}
"""
import json, glob, os, re, html, hashlib, sys, time, unicodedata
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, unquote
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = os.path.join(ROOT, "research", "pages")
OUT = os.path.join(ROOT, "research", "quote_check.json")
os.makedirs(PAGES, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (compatible; nyc-fiction-homes-verify/1.0)"}


def fetch_url(url):
    host = urlparse(url).hostname or ""
    if host.endswith("wikipedia.org") and "/wiki/" in url:
        title = url.split("/wiki/", 1)[1].split("#")[0]
        return f"https://{host}/api/rest_v1/page/html/{title}"
    if host.endswith(".fandom.com") and "/wiki/" in url:
        title = unquote(url.split("/wiki/", 1)[1].split("#")[0])
        return f"https://{host}/api.php?action=parse&page={title}&prop=text&redirects=1&format=json&formatversion=2"
    return url


def page_text(url):
    p = os.path.join(PAGES, hashlib.sha1(url.encode()).hexdigest()[:16] + ".txt")
    if os.path.exists(p):
        return open(p).read() or None
    txt = ""
    try:
        for attempt in range(5):
            r = requests.get(fetch_url(url), headers=UA, timeout=40)
            if r.status_code != 429:
                break
            time.sleep(4 * (attempt + 1))
        if r.ok:
            try:
                raw = r.content.decode("utf-8")
            except UnicodeDecodeError:
                raw = r.text
            if "api.php" in r.url:
                try:
                    raw = r.json()["parse"]["text"]
                    if isinstance(raw, dict):  # older api format
                        raw = raw.get("*", "")
                except Exception:
                    pass
            raw = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", raw)
            raw = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</h\d>|</div>", "\n", raw)
            txt = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    except Exception as e:
        print("fetch failed", url, e, file=sys.stderr)
    if txt:  # never cache a failed or rate-limited fetch as an empty page
        open(p, "w").write(txt)
    return txt or None


def norm(s):
    s = unicodedata.normalize("NFKC", s).replace("\u00ad", "")  # soft hyphens
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("—", "-").replace("–", "-").replace("_", "")
    s = re.sub(r"\[\s*(?:\d+|[a-z]|citation needed|note \d+)\s*\]", "", s, flags=re.I)  # wikipedia footnote marks
    s = re.sub(r"\s+", " ", s).strip().lower()
    s = re.sub(r" ([,.;:!?')])", r"\1", s)   # html text leaves spaces before punctuation at link edges
    s = re.sub(r"([(]) ", r"\1", s)
    return s


def toks(s):
    return [t for t in re.findall(r"[a-z0-9]+", norm(s)) if len(t) > 2 or t.isdigit()]


def check(quote, text):
    nq, nt = norm(quote), norm(text)
    nq_strip = nq.strip(' ."\'')
    if nq_strip and nq_strip in nt:
        return "verified", quote
    frags = [f.strip(' ."\'') for f in re.split(r"\.\.\.|…|\s-\s", nq) if len(f.split()) >= 4]
    if frags and all(f in nt for f in frags):
        return "verified", quote
    # look for the page sentence that best carries the quote's words
    qt = set(toks(quote))
    if not qt:
        return "failed", None
    nums = {t for t in qt if t.isdigit()}
    clean = re.sub(r"\[\s*(?:\d+|[a-z]|citation needed|note \d+)\s*\]", "", text, flags=re.I)
    sents = re.split(r"(?<=[.!?])\s+|\n+", re.sub(r"[ \t]+", " ", clean))
    best, score = None, 0.0
    for s in sents:
        w = s.split()
        if not 5 <= len(w) <= 40:
            continue
        st = set(toks(s))
        if nums and not nums <= st:
            continue  # a replacement must keep every number (house numbers, years)
        sc = len(qt & st) / len(qt)
        if sc > score:
            best, score = re.sub(r"\s+([,.;:!?')])", r"\1", re.sub(r"\s+", " ", s)).strip(), sc
    if best and score >= 0.6:
        return "replaced", best
    return "failed", None


def main():
    pairs = {}
    for f in glob.glob(os.path.join(ROOT, "research", "raw", "*.json")):
        for r in json.load(open(f)):
            for u, q in ((r.get("source_url"), r.get("source_quote")), (r.get("source2_url"), r.get("source2_quote"))):
                if u and q:
                    pairs[f"{u}||{q}"] = (u, q)
    urls = sorted({u for u, _ in pairs.values()})
    wiki = [u for u in urls if "wikipedia.org" in u]
    other = [u for u in urls if u not in wiki]
    with ThreadPoolExecutor(1) as ex: list(ex.map(page_text, wiki))
    with ThreadPoolExecutor(8) as ex: list(ex.map(page_text, other))
    out, tally = {}, {}
    for k, (u, q) in pairs.items():
        t = page_text(u)
        st, nq = ("unreachable", None) if not t else check(q, t)
        out[k] = {"status": st, "quote": nq}
        tally[st] = tally.get(st, 0) + 1
    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(tally)


if __name__ == "__main__":
    main()
