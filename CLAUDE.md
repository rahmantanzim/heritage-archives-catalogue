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
```

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
  readers/            # one reader per source format
  ingest.py           # read every source; `python -m ha_catalogue.ingest data/raw`
tests/            # pytest tests, one file per module
data/raw/         # original catalogue files, never edited by code
data/processed/   # pipeline output (git-ignored once added)
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

## Data sources (in `data/raw/`)

| File | Format | Notes |
|---|---|---|
| Catalogue 00 Main List | CSV, Unicode | Subject index (`Title`, `Reference`), e.g. "Abortion → see Family Planning 104". Use it to widen searches. |
| Catalogue 256 Posters | CSV, Unicode | ~4,530 rows: `Poster#, Topics, Publisher, Comments`. Some duplicate and malformed IDs, a few garbled English cells. |
| Catalogue 189 District Books | CSV, Unicode | ~3,600 rows: `Catalogue #, District/Topic, Title & Information`. IDs like `189.13 (527)`. |
| Catalogue 001–35, 190–242 | Word `.doc` | ID line (`1 (1)`) then a title line. Bijoy and English mixed. |
| Catalogue 243 Periodicals | Word `.doc` | Messy list; IDs in many formats. |
| Catalogue 243 Eid/Sharodiya | Word `.doc` | A table: catalogue no., name (Eng), name (Beng), address, subject, type, collection. |

Convert `.doc` files to `.docx` first (Word: Save As → .docx) so `python-docx`
can read paragraphs and tables.

## Roadmap

1. ~~Bijoy detection and conversion~~
2. ~~2a: CSV readers, ID parsing, garbled-English recovery~~
   2b: Word readers (.docx). 2c: data-quality report (CSV/HTML)
3. PostgreSQL storage (SQLAlchemy, Alembic migrations)
4. Search API (FastAPI, Postgres full-text and trigram search, subject index)
5. Tests in CI (GitHub Actions) and Docker Compose
6. OCR for scanned items (Tesseract, Bengali + English)
7. Stretch: semantic search with pgvector

Keep the README's status list in sync when a step is done.
