# Heritage Archives Catalogue

Ingestion, cleaning and search for the catalogue of
[Heritage Archives Bangladesh](https://heritage-archives.org), an independent
archive in Rajshahi holding about 30,000 periodical issues, 10,000 local
history books, posters, leaflets and theses.

## The problem

Heritage Archives Bangladesh has collected for over twenty years, and its
catalogue grew the same way: in Word files, Excel sheets and CSVs, typed by
different people with different tools. Today that causes five problems.

1. **No single place to search.** The website shows each catalogue as its own
   table. To find every item about a topic, a researcher has to open 13+
   catalogues one by one.
2. **Bengali that cannot be read or searched.** Much of the older Bengali was
   typed with the legacy Bijoy keyboard. The file stores Latin characters that
   one font draws as Bengali, so outside that font `Kv‡e`yj Bmjvg` appears
   instead of `কাবেদুল ইসলাম`. Search engines and databases see the Latin text.
3. **English that was turned into nonsense.** An earlier conversion ran English
   cells through a Bijoy converter too, so "Rajshahi University" became
   `জধলংযধযর টহরাবৎংরঃু`.
4. **IDs in many formats.** The same kind of ID appears as `189.13 (527)`,
   `189.1.(29A)`, `36 RAB (1)`, `CD-01` or `222a (21-2-1927)`.
5. **Hidden mistakes.** Duplicate IDs (61 rows share `189.9a (146)`), rows
   split in two, and dates that Excel cut to `5-Nov` with no year. Nobody knew
   how many, or where.

## What this project does

It reads every catalogue file, cleans it, and loads it into one database with
a search API. It never changes data silently: each record keeps its original
text next to the cleaned text, and every problem found is recorded with its
file and row number.

| Before | After |
|---|---|
| 13 catalogue files in 8 different layouts | One PostgreSQL database of 35,254 records |
| `Kv‡e`yj Bmjvg` (legacy Bijoy) | কাবেদুল ইসলাম (Unicode), in 1,232 records |
| `জধলংযধযর টহরাবৎংরঃু` | Rajshahi University, in 513 records |
| `189.1.(29A)`, `36 RAB (1)` | One ID format: `189.1/29a`, `36rab/1` |
| Mistakes nobody could count | 348 problems listed by file and row, ready to fix |
| One catalogue table at a time | One search across all catalogues, Bengali or English, in under 100 ms |

## Measured accuracy

The cleaning was measured, not just tested on chosen examples. 200 real cells
were picked at random (100 converted from Bijoy, 40 recovered English, and 60
cells the pipeline left alone, to catch misses), and a Bengali reader checked
each one by hand. The first measurement found four repeated error patterns in
the open-source converter; fixing them raised accuracy:

| Group | Before | After |
|---|---|---|
| All 200 cells | 91.0% | **98.0%** |
| Bijoy converted to Unicode | 83.0% | **96.0%** |
| English recovered | 97.5% | **100%** |
| Cells correctly left alone | 100% | **100%** |

Two of the four remaining errors are typing mistakes in the source. CI fails
if accuracy ever drops below the saved baseline (`data/eval/baseline.json`).
Run it yourself: `python -m ha_catalogue.evaluation data/eval/conversion_eval.csv`.

## Why it matters

- **For researchers:** one search covers the whole collection, in either
  language. A search for "posters" also finds every item in the poster
  catalogue, through the archive's own subject index.
- **For the archive's staff:** a precise to-do list of 348 problems. Instead of "the catalogue
  has errors somewhere", they get "row 1050 of the district books file repeats
  ID 189.9a (146)".
- **For the collection's future:** clean Unicode text with standard IDs is
  the base everything else needs: a new website, OCR of scanned pages, and
  AI-assisted search. None of those work on Bijoy text or on IDs in 20 formats.

## Status

- [x] Detect Bijoy text and convert it to Unicode Bengali
- [x] Recover English that was wrongly converted into Bengali letters
- [x] Read all 13 CSV catalogues: category catalogues, numbered lists
      (posters, leaflets), theses, biography lists and index, subject index
- [x] PostgreSQL storage with Alembic migrations
- [x] Search API (FastAPI): English and Bengali, widened by the subject index
- [x] Tests in GitHub Actions against a real PostgreSQL
- [x] One-command demo with Docker and a committed sample of the data
- [ ] Data-quality report
- [ ] OCR for scanned items

## Results so far

13 catalogue files (CSV, exported from the archive's Word and Excel
catalogues) plus the subject index:

| | |
|---|---|
| Items loaded | 35,254 |
| Subject index entries | 781 |
| Items with legacy Bijoy text converted to Unicode | 1,232 |
| Items with English recovered from garbled Bengali letters | 513 |
| Duplicate IDs found (kept and flagged) | 157 |
| Data problems found, each with its file and row | 348 |

## Try it in 2 minutes

You only need [Docker](https://www.docker.com/products/docker-desktop/).

```sh
git clone https://github.com/rahmantanzim/heritage-archives-catalogue.git
cd heritage-archives-catalogue
cp .env.example .env
docker compose up
```

When the log says `Uvicorn running`, open **http://localhost:8000/docs** and try
`GET /items` with `q` = `যশোর`, `Rajshahi University` or `posters`.

This loads `data/sample/`: 1,123 real records chosen so every feature shows up
(legacy Bijoy text, garbled English, duplicate and broken IDs, split rows).
The results above come from the full catalogue of 35,254 records, which is
kept out of the repository; it is available from Heritage Archives on request.

| Endpoint | What it does |
|---|---|
| `GET /items?q=যশোর` | Search titles, subjects, publishers and notes (Bengali or English) |
| `GET /items?q=posters` | Subject index terms widen the search to whole catalogues |
| `GET /items?catalogue=189.13` | All items in one catalogue |
| `GET /items/256/13` | One ID; returns every copy if the source has duplicates |
| `GET /issues/summary` | Data-quality problems found, by kind |

## Develop

Requires Python 3.12+ and Docker.

```sh
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest                                   # database tests skip without a test DB
```

Run the database in Docker and the Python code on your computer:

```sh
cp .env.example .env                     # set your own password, in both places
docker compose up -d db
alembic upgrade head
python -m ha_catalogue.load data/sample  # or data/raw for the full catalogue
uvicorn ha_catalogue.api:create_app --factory --reload
```

Database tests need a database whose name ends in `_test`:

```sh
docker compose exec db createdb -U ha ha_catalogue_test
TEST_DATABASE_URL=postgresql+psycopg://ha:YOUR_PASSWORD@127.0.0.1:5433/ha_catalogue_test pytest
```

With the full catalogue in `data/raw/`, `python scripts/make_sample.py data/raw data/sample`
rebuilds the sample.

## How the conversion works

See [`src/ha_catalogue/encoding.py`](src/ha_catalogue/encoding.py). The
`bijoy2unicode` library does most of the work, but it places the reph (র্)
wrongly and crashes when a line ends with one, and it maps a few characters
wrongly. This project handles reph itself and fixes those characters. Every
rule was found by checking real catalogue lines, and each one is a test case.

## Garbled English

Some English cells were run through a Bijoy converter by mistake, so
"Rajshahi University" became `জধলংযধযর টহরাবৎংরঃু`. The mistake can be reversed
letter by letter. See [`garbled_english.py`](src/ha_catalogue/garbled_english.py).
A result is only accepted when it reads as English, so real Bengali such as
`রাজশাহী` is never touched. 513 items were recovered this way. A cell is only treated as garbled when it has no real English letters in it, because the converter garbled whole cells.

## Roadmap

Planned, not built yet. The full plan is in
[`docs/product-plan.md`](docs/product-plan.md).

- **Phase 1, public catalogue (planned, December 2026):** a read-only website
  with search, category pages, item pages and filters.
- **Phase 2, admin panel (planned, early 2027):** staff log in, upload files,
  preview and approve changes, and edit single records.
- **Phase 3, smarter search (planned):** transliteration ("Rabindranath" finds
  রবীন্দ্রনাথ), meaning-based and hybrid search, checked against 50 real test
  searches.
- **Phases 4 and 5 (planned, later):** move heritage-archives.org off
  WordPress, then scans, OCR and an "Ask the archive" answer that always links
  to real items.
