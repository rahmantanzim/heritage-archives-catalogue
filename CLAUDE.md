# CLAUDE.md

Guidance for Claude when working in this repository.

## What this project is

A Python pipeline that turns the catalogue of Heritage Archives Bangladesh
(heritage-archives.org, an independent archive in Rajshahi) into one clean,
searchable catalogue.

The archive was founded by my father. Its catalogue grew from 2002 onwards
across Word files, Excel sheets and CSVs, and it has these problems:

- **Legacy Bijoy text.** Much of the older Bengali was typed with the Bijoy
  keyboard in a SutonnyMJ font. Outside that font it reads as `Kv‡e`yj Bmjvg`
  instead of `কাবেদুল ইসলাম`. Bijoy and English are often mixed line by line.
- **Inconsistent IDs.** One catalogue writes the same kind of ID as
  `189.13 (527)`, `J.243.1874`, `(J2188)`, `J (1726)` or `243.3211`.
- **Duplicates and broken rows.** Repeated IDs, empty rows, and English text
  that was wrongly converted to Bengali glyphs (`ঘবংঃষব ঘওউঙ` was "Nestle NIDO").

This is also a portfolio project for my application to Memorial University's
CAIR "Digital AI-Enabled Archive" internship. It should read as careful,
real-world data engineering: ingestion, metadata clean-up, search, and later
OCR and AI-ready search.

## How I want to work

- I'm a full-stack developer who mainly uses JavaScript/TypeScript. I'm
  learning Python, FastAPI and PostgreSQL through this project. I learn what I
  need for the current step, not everything at once.
- **Use plain English and short sentences.** Explain what each new piece does
  and why, in simple words. No jargon without a one-line explanation.
- **Work in small steps.** One focused change at a time, each small enough
  that I can read it, run it and understand it before we move on.
- **I make the commits myself.** Don't commit or push. At the end of each step,
  suggest a short commit message in the imperative ("Add poster CSV reader").
- **Tell me what I must understand.** After each step, list the 2–3 things I
  should be able to explain in an interview.
- If I ask for something that would create technical debt or a hacky
  workaround, push back and suggest the sound alternative.

## Code standards

- Python 3.12. Type hints on every function. Prefer `dataclass(frozen=True)`
  for records.
- Keep business logic (parsing, cleaning, ID rules) separate from I/O (reading
  files, the database, the API), so the logic can be tested without them.
- One bad row must never stop a whole load. Keep the original value, record
  the problem, and carry on. Every problem goes into the data-quality report.
- Never silently change data. Every cleaning rule should be traceable: keep
  the original text next to the cleaned text.
- No placeholder code, no "TODO: implement later", no truncated files.
- Clear names over comments. Add a comment only to explain *why*, especially
  for Bengali/Bijoy rules.
- Use `logging`, not `print`, except in small CLI entry points.
- Write non-ASCII characters in code as escapes (`"\u09cd"`), with the
  character in a comment. Invisible and combining characters are otherwise
  impossible to review. Literal Bengali is fine in comments and test data.
- Schema changes need a new Alembic migration and a matching change in
  `db.py`.

## Testing

- Every cleaning or conversion rule gets a test, using a **real line from the
  catalogue** as the example. Note where it came from if it's not obvious.
- When a rule fixes a bug, add the failing example as a test first.
- Run before finishing any step:
  ```sh
  pytest
  ruff check .
  ruff format --check .
  ```

## Commands

```sh
source .venv/bin/activate        # always; the venv uses Python 3.12
pip install -e ".[dev]"          # after changing pyproject.toml
pytest                           # all tests
pytest tests/test_encoding.py -v # one file
ruff check . && ruff format .    # lint and format
python -m ha_catalogue.encoding "Kv‡e\`yj Bmjvg"   # try the converter

docker compose up                    # everything: DB + API loaded with DATA_DIR
docker compose up -d db              # PostgreSQL only (needs .env, see .env.example)
alembic upgrade head                 # create/upgrade tables
python -m ha_catalogue.load data/raw # load the catalogue
uvicorn ha_catalogue.api:create_app --factory --reload   # API at :8000/docs
TEST_DATABASE_URL=postgresql+psycopg://ha:PASSWORD@127.0.0.1:5433/ha_catalogue_test pytest
```

Database tests only run when TEST_DATABASE_URL is set, and refuse any
database whose name doesn't end in `_test`. CI (GitHub Actions) always runs
them against PostgreSQL 16.

On this Mac, plain `python3` is Apple's Python 3.9. Never create the venv with
it. Use `python3.12 -m venv .venv`.

## Layout

```
src/ha_catalogue/
  encoding.py         # Bijoy detection and Bijoy -> Unicode conversion
  english.py          # "does this Latin text read as English?" test
  garbled_english.py  # undo English that was wrongly turned into Bengali letters
  cleaning.py         # clean_cell(): the one function readers use to clean text
  ids.py              # parse the many ID formats into catalogue + number
  models.py           # CatalogueItem, SubjectEntry, Issue, ReadResult
  quality.py          # checks across all items (duplicate IDs)
  readers/            # one module per source shape:
    _common.py          #   shared helpers (rows, cells, issues)
    category_catalogue.py  # ID, category, title (most files)
    numbered_list.py    #   posters 256, leaflets 180
    theses.py           #   catalogue 82
    biography_index.py  #   36 PC: person -> item, grouped by item
    subject_index.py    #   catalogue 00
  ingest.py           # read every source; `python -m ha_catalogue.ingest data/raw`
  settings.py         # DATABASE_URL from env or .env (pydantic-settings)
  db.py               # SQLAlchemy tables: items, subjects, issues
  text.py             # search_key(): NFC + casefold, used for load and search
  load.py             # replace all data in one transaction; `python -m ha_catalogue.load`
  search.py           # search logic (no HTTP), subject-index widening
  api.py              # FastAPI app factory: create_app()
migrations/           # Alembic; one file per schema change, never edit published ones
tests/            # pytest tests, one file per module
data/raw/         # the full catalogue: NOT in git (git-ignored), local only
data/sample/      # ~100 real rows per file, in git; built by scripts/make_sample.py
scripts/          # make_sample.py: rebuild the sample from data/raw
docker/           # entrypoint.sh: migrate, load DATA_DIR, start the API
Dockerfile        # the API image used by `docker compose up`
```

## Bijoy conversion: rules already learned

See `src/ha_catalogue/encoding.py`. Don't remove these rules without a test
showing they're wrong:

- The `bijoy2unicode` library places reph (র্, Bijoy `©`) wrongly and crashes
  when a line ends with one. We swap `©` for a private-use marker, convert, then
  put `র্` in front of the consonant cluster the marker follows.
- Pre-fixes before conversion: `šÍ`→`š—` (ন্ত), `ÿ`→`¶` (ক্ষ), `Ð`→`Û` (ণ্ড),
  `æ`→`z` (ু after র).
- Text that already contains Unicode Bengali is never treated as Bijoy.
- Cells can mix English and Bijoy. `normalize()` splits a cell at `, ; :` and
  before `see`, and converts only the Bijoy sections. Cross-references
  (`see 400.13 (93)`) and labels like `(S)` are kept as written.
- The library crashes on some short strings. `to_unicode()` pads with two
  spaces and strips them after.
- Some errors are in the source itself (e.g. `AeR©vfvi`, where the typist put
  the reph on the wrong letter). Flag these for human review. Don't guess.

I read Bengali, so I validate conversion output by hand. When unsure whether
a conversion is right, show me the before and after and ask.

## Garbled English: rules already learned

Some English cells were run through a Bijoy converter, e.g. "Nestle NIDO"
became `ঘবংঃষব ঘওউঙ`. `garbled_english.py` maps each letter back and accepts the
result only if `english.reads_as_english()` passes. Real Bengali like
`রাজশাহী` maps to `ivRkvnx`, which fails that test and is left alone. The
converter also moved "w" (ি) after the next letter, so we move it back
("Neswpaper" -> "Newspaper").

## IDs and records

- Standard item ID: `catalogue/number`, e.g. `189.13/527`, `256/12`.
  Lowercase letters (`29A` -> `29a`). The source ID is kept in `id_original`.
- Duplicate IDs are reported, never dropped. 61 rows of catalogue 189 share
  `189.9a (146)`, probably a fill-down mistake in the spreadsheet.
- A poster row with no number but some text continues the poster above.
- `3476-3500 duvKv` (ফাঁকা) means numbers kept blank on purpose.

## Data sources (in `data/raw/`, sample in `data/sample/`)

The full catalogue is kept out of git (decision: the archive's data isn't
published in full; visitors use the sample). Tests and CI use only
`data/sample/` and small inline CSVs. `tests/test_sample_data.py` checks that
the sample still shows every fix and issue kind; rebuild it with
`python scripts/make_sample.py data/raw data/sample` after reader changes.

All sources are Unicode CSV exports of the archive's catalogues. The file ->
reader mapping lives in `ingest.SOURCES`.

| File | Reader | Notes |
|---|---|---|
| catalogue-000-main-list.csv | subject index | "Abortion -> see Family Planning 104". Widens searches. |
| catalogue-001-035, 037-130, 131-188, 189-district-books-1-32, 190-242, 250-399 | category catalogue | `ID (n)`, category, title. `131` alone = section heading. No ID + title = continues the item above. 190-242 is mostly Bijoy. 37-130 has a "Kept at" column. |
| catalogue-036-rab/naz-biography, 036.4-biography-pms | category catalogue, title only | `36 RAB (1)` -> `36rab/1`. |
| catalogue-036-pc-biography-index | biography index | Person -> `36 PC (n)`. Grouped: one item per ID listing every person. |
| catalogue-082-theses | theses | `82.1`, `[82.148]`, `400.17 (152) [82.148]` (cross-listed). |
| catalogue-180-leaflets, 256-posters | numbered list | Number, topic, publisher, date/comments. `1901-2000` = blank range. Leaflet dates are Excel-mangled (`5-Nov`, no year). |

Known source problems (flag, never guess): 61 rows share `189.9a (146)`;
`241 (10` is missing a bracket; volume names act as numbers
(`91c (দ্বাদশ খণ্ড)`).

## Roadmap

1. ~~Bijoy detection and conversion~~
2. ~~2a: CSV readers, ID parsing, garbled-English recovery~~
   ~~2b: readers for all 13 CSV catalogues~~. 2c: data-quality report (CSV/HTML)
3. ~~PostgreSQL storage (SQLAlchemy, Alembic migrations)~~
4. ~~Search API (FastAPI, trigram-indexed search, subject index)~~
5. ~~Tests in CI (GitHub Actions) and Docker Compose~~
6. OCR for scanned items (Tesseract, Bengali + English)
7. Stretch: semantic search with pgvector

Keep the README's status list in sync when a step is done.
