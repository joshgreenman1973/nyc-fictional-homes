# Research brief: where fictional New Yorkers lived

Goal: a precise map of the homes of fictional characters in New York City (five boroughs only), across books, film, TV, theater and comics, from the Dutch colony to now. The dataset is the product. Precision and honesty about precision matter more than count.

## Hard rules
1. Five boroughs only. No West Egg, Yonkers, New Jersey, Long Island suburbs, Westchester. Riverdale and Forest Hills count; Hoboken does not.
2. Fictional characters only. No biopics of real people, no real people's homes. A real person fictionalized under their own name (e.g., in a historical novel) is out.
3. A HOME: where a character lived (apartment, house, boarding house, hotel they lived in, rooms, a shelter, a doorway they slept in). Not a workplace, not a scene location, not where something was filmed unless that building plays the home.
4. EVERY record needs `source_url` (a page you actually fetched with WebFetch in this run) and `source_quote` (verbatim text copied from that page, 40 words max, that supports the location). No fetched URL + verbatim quote = drop the record. Never reconstruct a URL or a quote from memory. For public-domain works, Project Gutenberg / Wikisource text of the work itself is the best source (quote the work). Otherwise Wikipedia, the publisher, reputable press (NYT, New Yorker, Curbed, Untapped Cities, Scouting NY, Atlas Obscura), author interviews, or a well-documented fan wiki, in that order of preference.
5. If sources disagree, say so in `notes` and pick the better-sourced one, or emit both records.
6. Historical street numbers: Manhattan renumbered some streets and many buildings are gone. Note it in `notes` when you know of it. Do not "fix" an address silently.

## Precision grades (field `precision`) — pick the most honest one
- `address_in_work`: a street address stated in the work itself (text, dialogue, a letter, a shown envelope or sign).
- `building_in_work`: a specific real building or exact street corner named in the work (the Dakota, the Chelsea Hotel, "Fifth Avenue at 61st").
- `creator_stated`: the author, playwright or showrunner gave the address or building outside the work (interview, notes, letter).
- `screen_exterior`: film/TV only — the real building shown as the home's exterior. Use kind "exterior" for these.
- `block_inferred`: the work gives a street or block but no number ("East Seventies near Lexington"), or critics/fans pinned a building from clues in the work. Say whose inference in notes.
- `neighborhood`: only a neighborhood or district.
- `invented`: the address or street does not exist (10 Stigwood Avenue, 704 Hauser Street). Give where the work implies it is.

## Story address vs. filmed exterior
For film and TV, the address the story gives and the building the camera shows are often different (the Huxtables' 10 Stigwood Ave, Brooklyn vs. the exterior at 10 St. Luke's Place, Manhattan). Emit TWO records with the same `home_key`: one with `kind: "story"` and one with `kind: "exterior"`. If the exterior is outside NYC (e.g., shot in Los Angeles), still emit the exterior record with `exterior_outside_nyc: true` and `geocode_query: null`. For books and plays, kind is always "story".

## Record schema (JSON)
{
  "home_key": "slug-of-character-and-home, e.g. holly-golightly-e71st",
  "kind": "story" | "exterior",
  "character": "Holly Golightly",
  "household": "optional: other residents, e.g. 'with Cat'",
  "work": "Breakfast at Tiffany's",
  "medium": "book" | "film" | "tv" | "theater" | "comics",
  "creator": "Truman Capote",
  "work_year": 1958,              // first publication/release/premiere
  "setting_start": 1943,          // year(s) the character lives there in the story; best estimate
  "setting_end": 1944,
  "address_as_given": "a brownstone in the East Seventies",   // exactly as the work/source puts it
  "borough": "Manhattan",
  "neighborhood": "Upper East Side",
  "precision": "block_inferred",
  "geocode_query": "169 East 71st Street, Manhattan",  // a modern address or intersection a NYC geocoder can resolve to the RIGHT spot today; null if not geocodable
  "approx_lat": null, "approx_lon": null,   // only if geocode_query is null and you can place it (neighborhood centroid, vanished street); 5 decimals
  "radius_m": 0,      // your honest uncertainty radius in meters: ~0-30 for an exact address, ~100-300 for a block, 500-1500 for a neighborhood
  "exterior_outside_nyc": false,
  "notes": "one or two plain sentences: what is known, disputes, renumbering, whether the building survives",
  "source_url": "https://...",
  "source_quote": "verbatim from that page",
  "source2_url": null, "source2_quote": null
}

## Output
Write a JSON array to the file path given in your scope, pretty-printed, valid JSON (no comments). Validate it with `python3 -c "import json,sys; json.load(open(sys.argv[1]))" <path>` before finishing. Your final reply: the count, the five records you are least sure of and why, and anything notable you found but excluded. Keep the reply under 200 words.
