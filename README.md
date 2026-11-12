# Heritage Archives Catalogue

Ingestion, cleaning and search for the catalogue of
[Heritage Archives Bangladesh](https://heritage-archives.org), an independent
archive in Rajshahi holding about 30,000 periodical issues, 10,000 local
history books, posters, leaflets and theses.

## The problem

The catalogue has grown since 2002 across Word files, Excel sheets and CSVs.
Much of the older Bengali text was typed with the legacy Bijoy keyboard in a
SutonnyMJ font, so outside that font it reads as `Kv‡e`yj Bmjvg` instead of
`কাবেদুল ইসলাম` and cannot be searched. IDs are written in several formats, and
some are duplicated.

This project turns those sources into one clean, searchable catalogue.

## Status

- [x] Detect Bijoy text and convert it to Unicode Bengali
- [x] Recover English that was wrongly converted into Bengali letters
- [x] Read the CSV catalogues (posters, district books, subject index)
- [ ] Read the Word catalogues
- [ ] Data-quality report
- [ ] PostgreSQL storage
- [ ] Search API (FastAPI)
- [ ] OCR for scanned items

## Run it

Requires Python 3.11+.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Read the catalogues and print a summary:

```sh
python -m ha_catalogue.ingest data/raw
```

Convert a line yourself:

```sh
python -m ha_catalogue.encoding "Kv‡e`yj Bmjvg"
```

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
`রাজশাহী` is never touched. 346 poster records were recovered this way.
