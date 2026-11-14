"""Pick a random, labelled-by-hand evaluation set of catalogue cells.

Writes a CSV for a Bengali reader to check. Each row is one real cell with
the pipeline's output. The reader marks it correct (Y) or wrong (N) and,
if wrong, writes the right text. scripts/evaluate.py then measures accuracy.

The sample is stratified: a fixed number from each of four groups, so rare
cases (recovered English) are measured too, not only the common ones:

- bijoy_converted:   cells the pipeline converted from Bijoy
- english_recovered: cells the pipeline turned back into English
- latin_unchanged:   Latin-letter cells left alone (real English, or missed Bijoy?)
- bengali_unchanged: Unicode Bengali cells left alone (real, or missed garbled English?)

Run (needs the full data in data/raw/):
    python scripts/make_eval_set.py data/raw data/eval/conversion_eval.csv
"""

from __future__ import annotations

import csv
import random
import re
import sys
from pathlib import Path

from ha_catalogue.cleaning import Fix, clean_cell
from ha_catalogue.ingest import SOURCES

SEED = 2026  # fixed, so the same sample can be rebuilt
GROUP_SIZES = {
    "bijoy_converted": 100,
    "english_recovered": 40,
    "latin_unchanged": 30,
    "bengali_unchanged": 30,
}
MIN_LETTERS = 4  # skip cells too short to judge, like "-" or "1998"

_BENGALI = re.compile("[ঀ-৿]")
_LETTER = re.compile(r"[^\W\d_]")

COLUMNS = [
    "id",
    "group",
    "file",
    "row",
    "column",
    "original",
    "pipeline_output",
    "correct",
    "expected",
    "notes",
]


def _group(original: str, output: str | None, fix: Fix) -> str | None:
    if output is None or len(_LETTER.findall(original)) < MIN_LETTERS:
        return None
    if fix is Fix.BIJOY_CONVERTED:
        return "bijoy_converted"
    if fix is Fix.ENGLISH_RECOVERED:
        return "english_recovered"
    return "bengali_unchanged" if _BENGALI.search(original) else "latin_unchanged"


def collect_cells(raw_dir: Path) -> dict[str, list[dict[str, str]]]:
    groups: dict[str, list[dict[str, str]]] = {name: [] for name in GROUP_SIZES}
    seen: set[str] = set()
    for file_name in SOURCES:
        with (raw_dir / file_name).open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            next(reader, None)
            for row_number, cells in enumerate(reader, start=2):
                for column, raw in enumerate(cells[1:], start=1):  # column 0 is the ID
                    original = " ".join(raw.split())
                    if original in seen:  # the same text twice adds nothing
                        continue
                    cell = clean_cell(raw)
                    group = _group(original, cell.text, cell.fix)
                    if group is None:
                        continue
                    seen.add(original)
                    groups[group].append(
                        {
                            "group": group,
                            "file": file_name,
                            "row": str(row_number),
                            "column": str(column),
                            "original": original,
                            "pipeline_output": cell.text or "",
                        }
                    )
    return groups


def main(raw_dir: Path, out_path: Path) -> None:
    rng = random.Random(SEED)
    groups = collect_cells(raw_dir)
    chosen: list[dict[str, str]] = []
    for name, size in GROUP_SIZES.items():
        chosen.extend(rng.sample(groups[name], min(size, len(groups[name]))))
    rng.shuffle(chosen)  # mixed order, so the checker isn't primed by the group

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        for number, row in enumerate(chosen, start=1):
            writer.writerow({**row, "id": str(number), "correct": "", "expected": "", "notes": ""})
    for name in GROUP_SIZES:
        print(f"{name:20} {sum(r['group'] == name for r in chosen):>4}  (of {len(groups[name])})")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: python scripts/make_eval_set.py RAW_DIR OUT_CSV")
    main(Path(sys.argv[1]), Path(sys.argv[2]))
