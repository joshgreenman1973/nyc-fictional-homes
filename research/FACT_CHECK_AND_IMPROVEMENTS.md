# NYC Fictional Homes — Fact-Check & Improvement Report

This document audits the 516 raw records across `research/raw/*.json`, the 506 built records in `data/homes.json`, the QA problems in `research/qa_report.md`, and the quote/geocoding scripts (`scripts/verify_quotes.py` and `scripts/build.py`) in `/Users/joshgreenman/Experiments/nyc-fictional-homes/`.

## Quick Check: *Harriet the Spy*
- **Status:** Already included (`harriet-welsch-e87th`, ID `ef689aace3` in `research/raw/kids_comics.json` and `data/homes.json`).
- **Placement & Grade:** Yorkville at `"East Eighty-seventh Street in Manhattan"` (`geocode_query: "558 East 87th Street, Manhattan"`, `precision: "block_inferred"`, `radius_m: 150`), verified against [PopSpots NYC](https://www.popspotsnyc.com/juvenile_ya_and_childrens_books) (`"Her house is near Carl Schultz Park on East 87th Street."`) and [CityRealty](https://www.cityrealty.com/nyc/market-insight/features/trending-in-ny/valuing-homes-harriet-spy-stuart-little-other-childrens-book-characters/3461) (`"That would place Harriet's house at 558 East 87th Street, which is now on the market for $5,975,000."`).
- **Assessment:** Honest grade (`block_inferred`), since Louise Fitzhugh names East 87th Street near Carl Schurz Park and `558` is CityRealty's inference.

## 1. Cross-Batch Duplicates Escaping `build.py` Deduplication

In `scripts/build.py`, `rid(r)` computes record IDs from `sha1(f"{r.get('home_key','')}|{r.get('kind','story')}|{r.get('work','')}")`. Whenever two batches record the same character home under slightly different `home_key` slugs (or omit `medium` in `rid()`), either both survive as duplicate pins or one is mistakenly dropped:

1. **Francie Nolan — *A Tree Grows in Brooklyn* (`books_1900_1959.json` vs. `gaps_tree_grows.json`)**
   - `francie-nolan-williamsburg` (`4d9920ff90` in `research/raw/books_1900_1959.json`) places a generic `neighborhood`-level circle in Williamsburg (`40.711, -73.951`), citing [Wikipedia (`A Tree Grows in Brooklyn (novel)`)](https://en.wikipedia.org/wiki/A_Tree_Grows_in_Brooklyn_(novel)).
   - `research/raw/gaps_tree_grows.json` now maps all three specific Nolan apartments in Williamsburg: `nolan-bogart` (Bogart Street, citing [Internet Archive](https://archive.org/stream/ATreeGrowsInBrooklyn/A%20Tree%20Grows%20in%20Brooklyn_djvu.txt) and [Bushwick Daily](https://web.archive.org/web/20260427202539/https://bushwickdaily.com/news/1851-a-tree-grows-on-bogart-street-even-100-years-after-the-novel/)), `nolan-lorimer` (Lorimer Street, citing [Bookpackers](https://www.bookpackers.com/master-feed/2019/5/6/a-gift-of-a-day)), and `nolan-grand` (Grand Street and Graham Avenue, citing [EBSCO](https://www.ebsco.com/research-starters/literature-and-writing/tree-grows-brooklyn-analysis-setting)).
   - **Fix:** Remove `francie-nolan-williamsburg` from `research/raw/books_1900_1959.json` (or add `"4d9920ff90": {"drop": true}` to `research/overrides.json`) so Francie isn't mapped four times in Williamsburg.

2. **Carrie Meeber — *Sister Carrie* (`books_pre1900.json` vs. `books_1900_1959.json`)**
   - *Sister Carrie* (published November 1900) was researched in both `books_pre1900.json` and `books_1900_1959.json`. Five records shared identical `home_key`s and were dropped with warnings in `research/qa_report.md`, but Carrie and Lola Osborne's 17th Street room survived twice under two keys:
     - `carrie-lola-17th-st` (`88569f4e9a` in `books_1900_1959.json`, placed at `40.7385, -73.993`)
     - `carrie-lola-17th-street` (`84486f3f69` in `books_pre1900.json`, placed at `40.7378, -73.9919`)
   - **Fix:** Remove all *Sister Carrie* records from `research/raw/books_pre1900.json` after moving the two non-duplicated supporting records (`mrs-vance-218-w58th` and `drouet-imperial-hotel`) into `research/raw/books_1900_1959.json`. This eliminates the duplicate 17th Street pin and clears 5 warnings from `research/qa_report.md`.

3. **Ragged Dick — *Ragged Dick* (`books_pre1900.json` vs. `kids_comics.json`)**
   - Both of Ragged Dick's homes appear twice in `data/homes.json` with different `home_key`s:
     - Spruce Street box: `ragged-dick-box-spruce-street` (`b5f4dbe330`, `books_pre1900.json`) and `ragged-dick-spruce-street-box` (`9d80ef5d3a`, `kids_comics.json`), both at `40.711688, -74.005847`.
     - Mrs. Mooney's Mott Street lodging house: `ragged-dick-mott-street-mooney` (`1f04bb70bb`, `books_pre1900.json`, placed at Mott & Grand `40.719062, -73.996472`) and `ragged-dick-mott-street-lodging-house` (`90e49765e0`, `kids_comics.json`, hand-placed at `40.7155, -73.998`).
   - **Fix:** Remove the two *Ragged Dick* entries from `research/raw/books_pre1900.json` and keep Horatio Alger's juveniles consolidated in `research/raw/kids_comics.json` (retaining the `Mott Street and Grand Street, Manhattan` `geocode_query`).

4. **Precious Jones — *Push* (`books_1960_now.json`) vs. *Precious* (`film.json`)**
   - Both the novel record (`Push`, `books_1960_now.json`) and the film record (`Precious`, `film.json`) use `home_key: "precious-jones-harlem"` with `kind: "story"`. Because `home_key` is meant to pair a single work's `story` and `exterior` records, sharing `home_key` across the book and film links two `story` records together.
   - **Fix:** Rename the novel record's key in `research/raw/books_1960_now.json` to `precious-jones-harlem-push`.

5. **Patrick Bateman (*American Psycho*) & Sherman McCoy (*The Bonfire of the Vanities*) — Book vs. Film Collision in `rid()`**
   - In `research/qa_report.md`, `duplicate record dropped: Sherman McCoy / The Bonfire of the Vanities (film)` and `duplicate record dropped: Patrick Bateman / American Psycho (film)` occur because the novel (`books_1960_now.json`) and film (`film.json`) share the exact same `home_key`, `kind: "story"`, and `work` title, and `rid(r)` in `scripts/build.py` does not include `medium`.
   - As a result, the film `story` records are silently dropped, leaving `sherman-mccoy-park-ave` in `film.json` with only an `exterior` record (`800 Park Avenue`) paired to the *book* `story` record.
   - **Fix:** Include `r.get('medium','')` in `rid(r)` in `scripts/build.py`, and suffix the film `home_key`s (`patrick-bateman-w81st-film`, `sherman-mccoy-park-ave-film`).

6. **Duplicate Jessica Jones in `research/raw/tv.json`**
   - `research/raw/tv.json` contains a duplicate entry for `Jessica Jones / Jessica Jones` that gets dropped on build (`qa_report.md`). Remove the duplicate object from `research/raw/tv.json`.

## 2. Resolving the Remaining Problems in `research/qa_report.md`

1. **Rescue Eilis Lacey — *Brooklyn* (`ec0a42561e` in `research/raw/gaps_books_theater.json`)**
   - **Problem:** Completely dropped (`no source survived the quote check`) because [Design Observer](https://designobserver.com/nostalgia-trip/) timed out / blocked fetch.
   - **Fix:** Replace `source_url` with a fetchable source such as [Wikipedia (`Brooklyn (novel)`)](https://en.wikipedia.org/wiki/Brooklyn_(novel)) or [LitCharts (`Brooklyn`)](https://www.litcharts.com/lit/brooklyn/summary) quoting Eilis's boarding house on Clinton Street in Brooklyn.

2. **Resolve Princeton — *Avenue Q* (`7f046358f8` in `research/raw/theater.json`)**
   - **Problem:** Dropped on every build (`borough None`) because the musical jokes that Avenue Q is in an unnamed `"outer-outer borough"` (citing [Wikipedia (`Avenue Q`)](https://en.wikipedia.org/wiki/Avenue_Q)).
   - **Fix:** Either remove `princeton-avenue-q` from `research/raw/theater.json` (since unmappable homes are out of scope) or add `"7f046358f8": {"drop": true}` to `research/overrides.json` so it exits cleanly before QA reporting.

3. **Add Missing `setting_start` and `setting_end` Years (7 Records)**
   - **Jude St. Francis & Willem Ragnarsson — *A Little Life* (`5c2754d2b9` and `f2452ad296` in `research/raw/books_1960_now.json`, citing [Read the Places](https://readtheplaces.com/a-little-life/)):** Set `setting_start: 2000, setting_end: 2005` for `jude-willem-lispenard-street` and `setting_start: 2005, setting_end: 2015` for `jude-greene-street-loft` (noting in `notes` that Yanagihara leaves the contemporary timeline undated).
   - **Lenny Abramov — *Super Sad True Love Story* (`7fb65910c7` in `research/raw/books_1960_now.json`, citing [The Globe and Mail](https://www.theglobeandmail.com/arts/books-and-media/review-super-sad-true-love-story-by-gary-shteyngart/article4324748/)):** Set `setting_start: 2012, setting_end: 2013` (near-future setting relative to its 2010 publication).
   - **Four Marvel Comics Records in `research/raw/kids_comics.json`:** Set `setting_start` and `setting_end` to match their debut publication years:
     - `ben-grimm-yancy-street` (`e2599fb8bf`, [Wikipedia (`Thing`)](https://en.wikipedia.org/wiki/Thing_(comics))): `1961` / `1961`
     - `matt-murdock-hells-kitchen` (`021427bcea`, [Wikipedia (`Daredevil`)](https://en.wikipedia.org/wiki/Daredevil_(Marvel_Comics_character))): `1964` / `1964`
     - `luke-cage-harlem` (`2faa6c355d`, [Wikipedia (`Luke Cage`)](https://en.wikipedia.org/wiki/Luke_Cage)): `1972` / `1972`
     - `sam-wilson-harlem` (`63469c8601`, [Wikipedia (`Falcon`)](https://en.wikipedia.org/wiki/Falcon_(comics))): `1969` / `1969`

4. **Remove or Replace Broken `source2_url` Links (3 Records)**
   - **Sara Smolinsky — *Bread Givers* (`525ffc9eac` in `research/raw/gaps_books_theater.json`):** `source_url` on [Internet Archive](https://archive.org/download/breadgiversnovel00yezi_1/breadgiversnovel00yezi_1_djvu.txt) passed, while `source2_quote` (`"A longing came over me for the old kitchen in Hester Street."`) failed due to OCR differences in the DjVu text. Set `source2_url` and `source2_quote` to `null` (or match the exact OCR string in the cached file).
   - **Travis Bickle — *Taxi Driver* (`4d1f771264` in `research/raw/gaps_screen.json`):** `source_url` ([NYC in Film](https://nycinfilm.com/2025/08/20/taxi-driver-1976/)) passed, while `source2_url` ([Kinoafisha](https://www.kinoafisha.info/en/movies/923296/locations/)) is unreachable. Set `source2_url` and `source2_quote` to `null`.
   - **Liza Miller — *Younger* (`68c2e91ae5` in `research/raw/tv.json`):** `source_url` passed, while `source2_url` ([MovieMaps](https://moviemaps.org/episodes/2i6)) failed. Set `source2_url` and `source2_quote` to `null`.

## 3. Pipeline & Script Fixes (`scripts/verify_quotes.py` & `scripts/build.py`)

1. **UTF-8 Mojibake in Replaced Quotes (`research/quote_check.json` & `data/homes.json`)**
   - Two records have `â\x80\x99` mojibake in `data/homes.json` because their cached pages in `research/pages/` were saved before UTF-8 decoding was enforced in `scripts/verify_quotes.py`:
     - `bd835d55af` (Cesar Castillo — *The Mambo Kings Play Songs of Love*, `books_1960_now.json`): `"Flophouse on New York Cityâ\x80\x99s 125th Street and Lenox Avenue..."`
     - `61eda3dfc5` (Dez — *Desperately Seeking Susan*, `film.json`, citing [On the Set of New York](https://www.onthesetofnewyork.com/desperatelyseekingsusan.html)): `"Dezâ\x80\x99s Apartment, 6 West 19th Street (btw 5th and 6th Avenues) Manhattan."`
   - **Fix:** Delete the cached `.txt` files for those two URLs in `research/pages/` and re-run `python3 scripts/verify_quotes.py` and `python3 scripts/build.py`.

2. **Spaced Wikipedia Footnote Markers (`[ 52 ]`) and >40-Word Replacements in `scripts/verify_quotes.py`**
   - When `verify_quotes.py` fetches Wikipedia REST HTML and strips tags (`re.sub(r"<[^>]+>", " ", raw)`), footnote brackets gain internal spaces (`[ 52 ]`). Because `norm()` only strips `\[\d+\]` for comparison and `check()` returns the raw sentence `s` up to `70` words, replaced quotes in `data/homes.json` leak raw citation brackets and violate the 40-word limit:
     - `332215919a` (Dan Humphrey — *Gossip Girl*, `kids_comics.json`, citing [Wikipedia (`Gossip Girl`)](https://en.wikipedia.org/wiki/Gossip_Girl)): `"He lives in a run-down Upper West Side [ 52 ] [ 53 ] apartment with his father, Rufus Humphrey — a bohemian, beatnik editor of minor Beat Generation poets [ 52 ] — his younger sister, Jenny, who is three years his junior, and their cat, Marx."` (48 words).
     - `395dcc81de` (Liz Lemon — *30 Rock*, `tv.json`, citing [Wikipedia (`Liz Lemon`)](https://en.wikipedia.org/wiki/Liz_Lemon)): `"Since 2005, [ 25 ] Liz has lived in an apartment at 160 Riverside Drive..."`
   - **Fix:** In `scripts/verify_quotes.py`, strip `re.sub(r"\[\s*(?:\d+|[a-z]|citation needed)\s*\]", "", s, flags=re.I)` and collapse whitespace on `best` before returning `"replaced", best`, and change `if not 5 <= len(w) <= 70:` to `if not 5 <= len(w) <= 40:`.

3. **59 Unpaired `kind: "exterior"` Records Across `film.json`, `tv.json`, and `gaps_screen.json`**
   - `research/BRIEF.md` states: *"Emit TWO records with the same `home_key`: one with `kind: "story"` and one with `kind: "exterior"`."*
   - Currently, **59 character homes** in `data/homes.json` (including `holly-golightly-e71st` in *Breakfast at Tiffany's*, `phoebe-morton-street` in *Friends*, `kimmy-titus-apartment` in *Unbreakable Kimmy Schmidt*, `elliot-east-broadway` in *Mr. Robot*, `reagans-bay-ridge` in *Blue Bloods*, `sheffield-mansion` in *The Nanny*, `miranda-priestly-e73rd` and `andy-sachs-broome-st` in *The Devil Wears Prada*, `kathleen-kelly-w89th` and `joe-fox-riverside` in *You've Got Mail*, `harry-burns-e11th` and `jess-marie-w89th` in *When Harry Met Sally...*, and `paul-flophouse-st-marks` / `steven-e-houston` in *Kids*) have **only** a `kind: "exterior"` record (`precision: "screen_exterior"`) and no `kind: "story"` record.
   - **Fix:** Either add the corresponding `kind: "story"` records for those 59 homes (where the story location is stated or inferred in the work) or ensure the frontend and documentation explicitly treat standalone `screen_exterior` records as primary markers when a film/show gives no separate story address.

## 4. Precision Grade, Batch, & Placement Corrections

1. **Move 1990s/1960s Novels Out of Earlier Chronological Batches**
   - **Caleb Carr's *The Alienist* (`work_year: 1994`, IDs `907926cb97` and `beea86de41`) and *The Angel of Darkness* (`work_year: 1997`, ID `8351fd2495`)** are in `research/raw/books_pre1900.json` because they are set in 1896–1897, whereas every other book file is split by publication year (`work_year`). Move them to `research/raw/books_1960_now.json`.
   - **Sylvia Plath's *The Bell Jar* (`work_year: 1963`, ID `2f7bc73e95`)** is in `research/raw/books_1900_1959.json` because it is set in 1953. Move it to `research/raw/books_1960_now.json`.

2. **Precision Grade Corrections**
   - **John Schuyler Moore — *The Alienist* (`beea86de41`, `19 Washington Square North`) & *The Angel of Darkness* (`8351fd2495`, `34 Gramercy Park`):** Currently graded `block_inferred` (`radius_m: 30`), citing [17th Street blog](https://17thstreet.net/2015/08/09/following-the-footsteps-of-dr-kreizler-a-travel-blog-part-two/). Both house numbers are stated in Carr's text; upgrade `precision` to `address_in_work` (or verify directly against text).
   - **Esther Greenwood — *The Bell Jar* (`2f7bc73e95`, `"the Amazon hotel"` at `140 East 63rd Street`):** Currently graded `block_inferred` with `radius_m: 30`, citing [Wikipedia (`The Bell Jar`)](https://en.wikipedia.org/wiki/The_Bell_Jar). Because `"the Amazon hotel"` is a fictionalized name for a real building (the Barbizon Hotel for Women at 140 East 63rd Street), grade it `invented` (matching how `"the Bramford"` in *Rosemary's Baby* and `"the Arconia"` in *Only Murders in the Building* are graded) and add a `source2_url` that explicitly connects the Amazon to the Barbizon at 140 East 63rd Street.
   - **George Costanza (`78eaa4b24e`, `321 West 90th Street`) & Elaine Benes (`90ec34f7bd` `17 E. 7th St.`, `bd433e759a` `16 W. 75th St.`, `4a20f3ebcb` `78 W. 86th St.`) in *Seinfeld* (`tv.json`):** All four have exact street numbers and `radius_m: 25`, but are graded `block_inferred`. Where the number appears in dialogue/buzzers/official show maps (e.g., `"The Pothole"` for 86th Street), upgrade to `address_in_work` or clarify in `address_as_given` what the episode states vs. what the fan map infers.

3. **De-Stack Identical Hand-Placed Coordinates (`placed_by: "approx"`)**
   - Seven Greenwich Village `neighborhood` records (`8536ce7190` *The Story of a New York House*, `56cf1da566` *The Iceman Cometh*, `42c94cf21a` *The Sign in Sidney Brustein's Window*, `e2f9b9a2b8` *Wait Until Dark*, `af90db44b2` *Kate & Allie*, `3b5f98bc2a` *Slaves of New York*, and `951cb42bdf` *The Princess Diaries*) all share the exact coordinate `40.7336, -74.0027`, stacking 7 markers on top of each other.
   - Specifically:
     - **Harry Hope's saloon and rooming house (*The Iceman Cometh*, `56cf1da566`):** O'Neill modeled Harry Hope's explicitly on the Golden Swan ("Hell Hole") at the corner of **West 4th Street and Sixth Avenue** (or Jimmy-the-Priest's on Fulton Street on the Lower West Side waterfront). Updating `notes` and placing it at West 4th & Sixth Ave (`40.7317, -74.0005`) or slightly offsetting the remaining Village neighborhood centroids prevents marker overlap.
     - **Susy and Sam Hendrix (*Wait Until Dark*, `e2f9b9a2b8`):** In both the play and film, their basement apartment is at **478 St. Luke's Place** (an invented house number on real St. Luke's Place in the West Village, filmed at `4 St. Luke's Place`). Placing it on St. Luke's Place (`40.7295, -74.0059`, `precision: "invented"` or `"block_inferred"`) is much more accurate than a generic Village centroid.
   - Similarly, three Williamsburg TV records (`a84d2c196c` Dan Humphrey in *Gossip Girl*, `9710b77277` Max & Caroline in *2 Broke Girls*, `3119fb95ed` Maggie & Liza in *Younger*) share `40.7142, -73.9613`, and two Harlem comics records (`2faa6c355d` Luke Cage, `63469c8601` Sam Wilson) plus `d679208bdb` (*Behold the Dreamers*) share `40.8116, -73.9465`. Jittering neighborhood centroids by 150–300 meters keeps every circle clickable.

## 5. High-Priority Content Gaps for the Next Research Pass

Current raw record distribution by borough: **Manhattan (404)**, **Brooklyn (71)**, **Queens (18)**, **Bronx (12)**, **Staten Island (2)**. A dedicated outer-borough and canonical-gaps pass (`research/raw/gaps_boroughs_canon.json`) should target:

### Staten Island & Outer Boroughs
- ***What We Do in the Shadows* (TV, 2019, Jemaine Clement):** Nandor, Laszlo, Nadja, Colin Robinson, and Guillermo's vampire residence in Staten Island (`story` in Tompkinsville/St. George, Staten Island; `exterior` in Toronto with `exterior_outside_nyc: true`).
- ***Underworld* (book, 1997, Don DeLillo):** Nick Shay and Klara Sax in the 1950s Italian Bronx (Belmont / Arthur Avenue neighborhood).
- ***The Wanderers* (book, 1974, Richard Price / film, 1979, Philip Kaufman):** Richie, Joey, and the Wanderers in the Bronx (Pelham Parkway housing project).
- ***Native Speaker* (book, 1995, Chang-rae Lee):** Henry Park and his father in Flushing / Queens.
- ***Nora from Queens* (TV, 2020, Awkwafina & Teresa Hsiao):** Nora Lin living with her dad and grandmother in Flushing, Queens (fits the *Seinfeld* / *Everybody Hates Chris* sitcom-version rule in `README.md`).
- ***Spider-Man: Into the Spider-Verse* (film, 2018) / *Ultimate Comics: Spider-Man* (comics, 2011, Brian Michael Bendis & Sara Pichelli):** Miles Morales's family apartment in Brooklyn (and his Visions Academy dorm room).
- ***My Name Is Asher Lev* (book, 1972, Chaim Potok):** Asher Lev's family apartment on Brooklyn Parkway (Eastern Parkway) in Crown Heights, Brooklyn.
- ***Another Brooklyn* (book, 2016, Jacqueline Woodson):** August growing up in 1970s Bushwick, Brooklyn.
- ***Desperate Characters* (book, 1970, Paula Fox):** Otto and Sophie Bentwood's brownstone in Brooklyn Heights (on fictionalized "Bentham Street").
- ***Sophie's Choice* (book, 1979, William Styron):** Yetta Zimmerman's "Pink Palace" boarding house in Flatbush near Prospect Park, Brooklyn (currently only the 1982 film is in `film.json`).
- ***Brooklyn Nine-Nine* (TV, 2013):** Jake Peralta's apartment (inherited from Gina Linetti) and Jake & Amy's apartment in Brooklyn (plus exterior filming locations).
- ***Bored to Death* (TV, 2009, Jonathan Ames):** Jonathan's apartment in Fort Greene / Clinton Hill, Brooklyn.

### Canonical Manhattan Literature, Theater, TV & Film
- ***Succession* (TV, 2018, Jesse Armstrong):**
  - Logan Roy's Upper East Side townhouse (`991 Fifth Avenue` exterior at East 80th Street).
  - Kendall Roy's Tribeca apartment / Rava's apartment (`67 Vestry Street` / Woolworth Tower Residences).
  - Shiv Roy and Tom Wambsgans's Tribeca duplex (`67 Vestry Street`).
- ***The Gilded Age* (TV, 2022, Julian Fellowes):**
  - Agnes van Rhijn and Ada Brook's brownstone at **East 61st Street and Fifth Avenue** (`building_in_work`).
  - George and Bertha Russell's new palace across the street at **East 61st Street and Fifth Avenue** (`building_in_work`).
- ***Invisible Man* (book, 1952, Ralph Ellison):**
  - The narrator's underground coal-cellar home illuminated by 1,369 Monopolated Light & Power bulbs `"in a border area"` of Harlem (currently only Mary Rambo's boarding house is mapped in `books_1900_1959.json`, missing the novel's famous prologue/epilogue home).
- ***Ragtime* (book, 1975, E. L. Doctorow):**
  - Currently only the 1998 musical is in `theater.json`; add the 1975 novel to `books_1960_now.json` for Tateh and the Little Girl on the Lower East Side and Mother's Younger Brother / Evelyn Nesbit in Manhattan (noting the family home in New Rochelle is outside the five boroughs).
- ***Flight of the Conchords* (TV, 2007, James Bobin, Jemaine Clement & Bret McKenzie):**
  - Bret and Jemaine's Chinatown apartment (`28 Henry Street` exterior in Two Bridges / Chinatown).
- ***Felicity* (TV, 1998, J. J. Abrams & Matt Reeves):**
  - Felicity Porter's dorm room at the fictional "University of New York" in Greenwich Village / Epstein Hall (`15 Washington Square North` / Greenwich Village).
- ***Law & Order* / *Law & Order: Special Victims Unit* (TV, 1990 / 1999, Dick Wolf):**
  - Olivia Benson's Upper West Side apartments and Lennie Briscoe's West Side apartment.
- ***Kojak* (TV, 1973) / *NYPD Blue* (TV, 1993) / *Barney Miller* (TV, 1975):**
  - Andy Sipowicz's apartment; Barney and Liz Miller's Greenwich Village apartment.
- ***High Maintenance* (TV, 2012/2016, Ben Sinclair & Katja Blichfeld):**
  - The Guy's Brooklyn apartment and RV.
- ***Pose* (TV, 2018, Ryan Murphy, Brad Falchuk & Steven Canals):**
  - Blanca Evangelista's House of Evangelista apartment in Manhattan/Bronx.
- ***Funnyhouse of a Negro* / *Frankie and Johnny in the Clair de Lune* / *Torch Song Trilogy*:**
  - Adrienne Kennedy's *Funnyhouse of a Negro* (1964, Upper West Side brownstone rooming house), Terrence McNally's *Frankie and Johnny in the Clair de Lune* (1987, Hell's Kitchen walk-up), and Harvey Fierstein's *Torch Song Trilogy* (1982, Arnold Beckoff's Brooklyn/Manhattan apartments).
- ***Harriet the Spy* (book, 1964, Louise Fitzhugh) — Secondary Homes on Her Spy Route:**
  - Harrison Withers's apartment (with his 26 cats) on East 82nd Street, Sport's apartment with his writer father on East 86th Street, and Mrs. Agatha K. Plumber's townhouse on East 87th Street.
