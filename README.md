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
- [ ] Read each catalogue source (CSV, Word)
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
