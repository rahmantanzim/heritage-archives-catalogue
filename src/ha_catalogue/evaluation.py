"""Measure how accurate the cleaning is, against cells checked by a person.

The evaluation set (data/eval/conversion_eval.csv) holds real cells picked at
random. A Bengali reader marked each pipeline output correct (Y) or wrong (N)
and, when wrong, wrote the right text in `expected`. This module re-runs the
CURRENT cleaning code on every original cell and compares it with that truth,
so a code change shows up as a better or worse score.

Run:
    python -m ha_catalogue.evaluation data/eval/conversion_eval.csv
    python -m ha_catalogue.evaluation data/eval/conversion_eval.csv --save-baseline

The baseline (data/eval/baseline.json) is the score the tests must not fall
below. Save it again after an improvement, so the bar only goes up.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from ha_catalogue.cleaning import clean_cell

YES, NO = "Y", "N"


class LabelError(ValueError):
    """The evaluation sheet is not fully or correctly labelled."""


@dataclass(frozen=True)
class Case:
    id: str
    group: str
    original: str
    truth: str


@dataclass(frozen=True)
class Outcome:
    case: Case
    output: str

    @property
    def correct(self) -> bool:
        return self.output == self.case.truth

    @property
    def similarity(self) -> float:
        """How close the output is to the truth, from 0.0 to 1.0, by character."""
        return SequenceMatcher(None, self.output, self.case.truth).ratio()


@dataclass(frozen=True)
class Score:
    correct: int
    total: int

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0


def load_cases(path: Path) -> list[Case]:
    """Read the labelled sheet. Raises LabelError if any row is unfinished."""
    cases: list[Case] = []
    problems: list[str] = []
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except UnicodeDecodeError as error:
        raise LabelError(
            f"{path} is not saved as UTF-8, so Bengali text can't be read. Re-save it as "
            '"CSV UTF-8" (Excel), "Unicode (UTF-8)" (Numbers), or download it from '
            "Google Sheets as .csv."
        ) from error
    for row in rows:
        mark = row["correct"].strip().upper()
        expected = " ".join(row["expected"].split())
        if mark == YES:
            truth = row["pipeline_output"]
        elif mark == NO and expected:
            truth = expected
        elif mark == NO:
            problems.append(f"row {row['id']}: marked N but `expected` is empty")
            continue
        else:
            problems.append(f"row {row['id']}: `correct` must be Y or N")
            continue
        cases.append(Case(row["id"], row["group"], row["original"], truth))
    if problems:
        shown = "\n".join(problems[:10])
        more = f"\n... and {len(problems) - 10} more" if len(problems) > 10 else ""
        raise LabelError(f"{len(problems)} rows need labelling:\n{shown}{more}")
    return cases


def evaluate(cases: list[Case]) -> list[Outcome]:
    return [Outcome(case, clean_cell(case.original).text or "") for case in cases]


def scores(outcomes: list[Outcome]) -> dict[str, Score]:
    """Accuracy overall ("all") and for each group."""
    totals: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for outcome in outcomes:
        for key in ("all", outcome.case.group):
            totals[key][0] += outcome.correct
            totals[key][1] += 1
    return {key: Score(correct, total) for key, (correct, total) in totals.items()}


def save_baseline(path: Path, result: dict[str, Score]) -> None:
    data = {key: round(score.accuracy, 4) for key, score in sorted(result.items())}
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load_baseline(path: Path) -> dict[str, float]:
    return json.loads(path.read_text(encoding="utf-8"))


def _report(outcomes: list[Outcome], result: dict[str, Score]) -> None:
    print(f"{'group':20} {'correct':>9} {'accuracy':>9}")
    for key, score in sorted(result.items(), key=lambda item: item[0] != "all"):
        print(f"{key:20} {score.correct:>4}/{score.total:<4} {score.accuracy:>8.1%}")
    wrong = [outcome for outcome in outcomes if not outcome.correct]
    if wrong:
        average = sum(outcome.similarity for outcome in wrong) / len(wrong)
        print(f"\n{len(wrong)} wrong; on average {average:.0%} similar to the right text:")
        for outcome in wrong:
            print(f"  #{outcome.case.id} [{outcome.case.group}] {outcome.case.original}")
            print(f"      got:      {outcome.output}")
            print(f"      expected: {outcome.case.truth}")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: python -m ha_catalogue.evaluation EVAL_CSV [--save-baseline]")
        return 2
    path = Path(argv[1])
    try:
        cases = load_cases(path)
    except LabelError as error:
        print(error)
        return 1
    outcomes = evaluate(cases)
    result = scores(outcomes)
    _report(outcomes, result)
    if "--save-baseline" in argv[2:]:
        baseline_path = path.with_name("baseline.json")
        save_baseline(baseline_path, result)
        print(f"\nSaved baseline to {baseline_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
