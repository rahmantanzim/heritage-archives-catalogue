"""Read every known catalogue file and print a short summary.

Run:  python -m ha_catalogue.ingest data/raw
"""

from __future__ import annotations

import sys
from collections import Counter
from collections.abc import Callable
from pathlib import Path

from ha_catalogue.models import ReadResult
from ha_catalogue.quality import find_duplicate_ids
from ha_catalogue.readers.csv_catalogues import (
    read_district_books,
    read_posters,
    read_subject_index,
)

Reader = Callable[[Path], ReadResult]

# File name -> reader. New sources are added here.
SOURCES: dict[str, Reader] = {
    "catalogue-000-main-list.csv": read_subject_index,
    "catalogue-189-district-books-1-32.csv": read_district_books,
    "catalogue-256-posters.csv": read_posters,
}


def read_all(raw_dir: Path) -> ReadResult:
    combined = ReadResult()
    for file_name, reader in SOURCES.items():
        path = raw_dir / file_name
        if not path.exists():
            raise FileNotFoundError(f"missing source file: {path}")
        result = reader(path)
        combined.items.extend(result.items)
        combined.subjects.extend(result.subjects)
        combined.issues.extend(result.issues)
        combined.skipped_empty_rows += result.skipped_empty_rows
    combined.issues.extend(find_duplicate_ids(combined.items))
    return combined


def main(argv: list[str]) -> int:
    raw_dir = Path(argv[1]) if len(argv) > 1 else Path("data/raw")
    result = read_all(raw_dir)

    print(f"Items:           {len(result.items)}")
    print(f"Subject entries: {len(result.subjects)}")
    print(f"Empty rows:      {result.skipped_empty_rows}")
    print("\nItems by source:")
    for source, count in Counter(i.source for i in result.items).most_common():
        print(f"  {source:45} {count}")
    print("\nCleaning applied:")
    for fix, count in Counter(f for i in result.items for f in i.fixes).most_common():
        print(f"  {fix:45} {count}")
    print("\nIssues:")
    for kind, count in Counter(i.kind for i in result.issues).most_common():
        print(f"  {kind:45} {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
