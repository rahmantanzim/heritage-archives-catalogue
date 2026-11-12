"""Build data/sample/ from the full catalogue in data/raw/.

The sample is what's committed to git, so anyone can run the project
without the full catalogue. For each source file it keeps:

- the header and the first FIRST_ROWS data rows, and
- a few rows around the first example of every cleaning fix and every
  kind of issue (Bijoy text, garbled English, duplicate IDs, broken IDs...),
  so the demo shows everything the pipeline does.

The subject index is small and is kept whole, because search uses it.

Run (needs the full data in data/raw/):
    python scripts/make_sample.py data/raw data/sample
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from ha_catalogue.ingest import SOURCES, read_all

FIRST_ROWS = 60
CONTEXT_ROWS = 5  # rows kept before and after each example
KEEP_WHOLE = frozenset({"catalogue-000-main-list.csv"})


def _rows_to_keep(raw_dir: Path) -> dict[str, set[int]]:
    """Row numbers (header = 1) to keep, per file."""
    result = read_all(raw_dir)
    examples: dict[str, dict[str, int]] = {name: {} for name in SOURCES}
    for item in result.items:
        for fix in item.fixes:
            examples[item.source].setdefault(str(fix), item.row)
    for issue in result.issues:
        examples[issue.source].setdefault(str(issue.kind), issue.row)

    keep: dict[str, set[int]] = {}
    for name, first_rows in examples.items():
        rows = set(range(1, FIRST_ROWS + 2))
        for row in first_rows.values():
            rows.update(range(max(2, row - CONTEXT_ROWS), row + CONTEXT_ROWS + 1))
        keep[name] = rows
    return keep


def make_sample(raw_dir: Path, sample_dir: Path) -> None:
    sample_dir.mkdir(parents=True, exist_ok=True)
    keep = _rows_to_keep(raw_dir)
    for name in SOURCES:
        with (raw_dir / name).open(encoding="utf-8-sig", newline="") as source:
            rows = list(csv.reader(source))
        if name not in KEEP_WHOLE:
            rows = [row for number, row in enumerate(rows, start=1) if number in keep[name]]
        with (sample_dir / name).open("w", encoding="utf-8", newline="") as target:
            csv.writer(target, lineterminator="\n").writerows(rows)
        print(f"{name:45} {len(rows) - 1:>5} rows")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: python scripts/make_sample.py RAW_DIR SAMPLE_DIR")
    make_sample(Path(sys.argv[1]), Path(sys.argv[2]))
