"""Read every known catalogue file and print a short summary.

Run:  python -m ha_catalogue.ingest data/raw
"""

from __future__ import annotations

import sys
from collections import Counter
from collections.abc import Callable
from functools import partial
from pathlib import Path

from ha_catalogue.models import ReadResult
from ha_catalogue.quality import find_duplicate_ids
from ha_catalogue.readers.biography_index import read_biography_index
from ha_catalogue.readers.category_catalogue import (
    STANDARD,
    TITLE_ONLY,
    WITH_KEPT_AT,
    read_category_catalogue,
)
from ha_catalogue.readers.numbered_list import LEAFLETS, POSTERS, read_numbered_list
from ha_catalogue.readers.subject_index import read_subject_index
from ha_catalogue.readers.theses import read_theses

Reader = Callable[[Path], ReadResult]

# File name -> reader. New sources are added here.
SOURCES: dict[str, Reader] = {
    "catalogue-000-main-list.csv": read_subject_index,
    "catalogue-001-035.csv": partial(read_category_catalogue, columns=STANDARD),
    "catalogue-036-rab-biography.csv": partial(read_category_catalogue, columns=TITLE_ONLY),
    "catalogue-036-naz-biography.csv": partial(read_category_catalogue, columns=TITLE_ONLY),
    "catalogue-036.4-biography-pms.csv": partial(read_category_catalogue, columns=TITLE_ONLY),
    "catalogue-036-pc-biography-index.csv": read_biography_index,
    "catalogue-037-130.csv": partial(read_category_catalogue, columns=WITH_KEPT_AT),
    "catalogue-082-theses.csv": read_theses,
    "catalogue-131-188.csv": partial(read_category_catalogue, columns=STANDARD),
    "catalogue-180-leaflets.csv": partial(read_numbered_list, layout=LEAFLETS),
    "catalogue-189-district-books-1-32.csv": partial(read_category_catalogue, columns=STANDARD),
    "catalogue-190-242.csv": partial(read_category_catalogue, columns=STANDARD),
    "catalogue-250-399.csv": partial(read_category_catalogue, columns=STANDARD),
    "catalogue-256-posters.csv": partial(read_numbered_list, layout=POSTERS),
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
        combined.section_headings += result.section_headings
    combined.issues.extend(find_duplicate_ids(combined.items))
    return combined


def main(argv: list[str]) -> int:
    raw_dir = Path(argv[1]) if len(argv) > 1 else Path("data/raw")
    result = read_all(raw_dir)

    print(f"Items:           {len(result.items)}")
    print(f"Subject entries: {len(result.subjects)}")
    print(f"Empty rows:      {result.skipped_empty_rows}")
    print(f"Section headings:{result.section_headings:>6}")
    print("\nItems by source:")
    for source, count in Counter(i.source for i in result.items).most_common():
        print(f"  {source:45} {count}")
    print("\nCleaning applied:")
    for fix, count in Counter(f for i in result.items for f in i.fixes).most_common():
        print(f"  {fix:45} {count}")
    print("\nProblems found (for a person to check):")
    for kind, count in Counter(i.kind for i in result.issues).most_common():
        print(f"  {kind:45} {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
