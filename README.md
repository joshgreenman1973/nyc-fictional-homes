# Fictional New Yorkers at home

A map of where characters in novels, plays, films, television and comics lived in New York City, from the 1750s to the 2020s. Every home links to a source and a short quotation that supports the location, and every mark is graded for how precisely the source pins it down.

Live page: https://joshgreenman1973.github.io/nyc-fictional-homes/

## What counts

- The five boroughs only. Gatsby's West Egg, the suburbs and New Jersey are out.
- Fictional characters only. Unnamed roles are left out. The exceptions are sitcom versions of real people living at invented or fictionalized addresses (Jerry Seinfeld at 129 West 81st, Chris Rock's childhood stand-in in Everybody Hates Chris), which are noted on their records.
- A home is where someone lived: an apartment, house, boarding house, hotel room they kept, or a museum they hid in. Workplaces and one-night scenes are left out.

## Precision grades

| Grade | Meaning | Mark |
|---|---|---|
| address_in_work | The work gives a street address | filled dot |
| building_in_work | The work names a building or an exact corner | filled dot |
| creator_stated | The author or show said where, outside the work | filled dot |
| screen_exterior | The real building filmed as the home's exterior | hollow ring |
| block_inferred | The work gives a block or a street between two cross streets | translucent circle |
| neighborhood | The work gives only a neighborhood | larger translucent circle |
| invented | The address does not exist; placed where the work implies | dashed circle |

When a show or film gives a home one address and shoots a different building, both are on the map with a thin line between them. The two records share a `home_key`.

## How it was built

1. **Research.** Seven first passes (books before 1900, 1900–1959, 1960 to now, children's books and comics, film, television, theater) each followed `research/BRIEF.md`. Later gap passes, also in `research/raw/`, cover famous homes the first passes missed, the outer boroughs, the Manhattan canon, Woody Allen, Spike Lee and Sidney Lumet, sitcoms and animation, and two families in detail: the All-of-a-Kind Family and the Nolans of A Tree Grows in Brooklyn. To add homes, write a new file in `research/raw/` and rerun the steps below. `research/FACT_CHECK_AND_IMPROVEMENTS.md` is an outside audit whose fixes have been applied.
2. **Quote check.** `scripts/verify_quotes.py` downloads every source page itself and looks for each quotation in the page text. A quote that appears is marked verified. A paraphrase whose meaning matches one real sentence on the page is replaced with that sentence, which must keep every number. A quote that matches nothing is dropped, and a home left with no source is dropped. Results are in `research/quote_check.json`.
3. **Placement.** `scripts/build.py` geocodes in this order: the city planning department's GeoSearch for street addresses (checking that the house number, borough and East or West side match), an OpenStreetMap street-grid index for corners (`scripts/fetch_streets.py` builds it), Nominatim for named landmarks, and hand placement from the description for everything else. Every point is checked against the borough boundary the source names. Hand fixes are in `research/overrides.json`. Problems from each build are listed in `research/qa_report.md`.
4. **Pictures.** `scripts/enrich.py` adds a promotional still and poster from TMDB for films and shows, and the lead image of the Wikipedia article (usually a cover or a production photo) for books, plays and comics. A photograph of the building is added only when a Wikipedia article or Wikimedia Commons photo names that building, or its house number and street, or when the building was matched by hand in `research/venue_titles.json`.

## Rebuilding

```
python3 scripts/fetch_streets.py      # once; about 80 MB, not committed
python3 scripts/verify_quotes.py
python3 scripts/build.py
TMDB_API_KEY=... python3 scripts/enrich.py
python3 -m http.server 8863
```

## Caveats

- Manhattan renumbered some streets in the 19th century, and many buildings named here are gone. A mark shows where an address falls on today's map.
- Television and film stills come from TMDB and are promotional images, not necessarily of the home.
- Coverage leans toward Manhattan, the canon and the English language, because that is where the sourcing is. Additions with a source are welcome.

Data: `data/homes.json`. Map data © OpenStreetMap contributors, basemap © CARTO.
