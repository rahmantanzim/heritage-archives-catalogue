"""Accuracy must never fall below the saved baseline.

Uses the hand-checked evaluation set in data/eval/. Skipped until the set is
labelled and a baseline is saved:

    python -m ha_catalogue.evaluation data/eval/conversion_eval.csv --save-baseline
"""

from pathlib import Path

import pytest

from ha_catalogue.evaluation import (
    Case,
    LabelError,
    evaluate,
    load_baseline,
    load_cases,
    scores,
)

EVAL_DIR = Path(__file__).resolve().parent.parent / "data" / "eval"
EVAL_SET = EVAL_DIR / "conversion_eval.csv"
BASELINE = EVAL_DIR / "baseline.json"
# Leeway for rounding in the saved baseline.
TOLERANCE = 0.0001


def _labelled_scores():
    if not BASELINE.exists():
        pytest.skip("no baseline yet: label data/eval/conversion_eval.csv, then save one")
    try:
        cases = load_cases(EVAL_SET)
    except LabelError as error:
        pytest.fail(f"a baseline exists but the evaluation set is not fully labelled: {error}")
    return scores(evaluate(cases)), load_baseline(BASELINE)


def test_accuracy_does_not_fall_below_baseline():
    result, baseline = _labelled_scores()
    for group, minimum in baseline.items():
        assert result[group].accuracy >= minimum - TOLERANCE, (
            f"{group}: accuracy {result[group].accuracy:.1%} fell below baseline {minimum:.1%}"
        )


def test_scoring_counts_matches_per_group():
    cases = [
        Case("1", "bijoy_converted", "Kv‡e`yj Bmjvg", "কাবেদুল ইসলাম"),
        Case("2", "bijoy_converted", "wbe©vPb", "something else"),
        Case("3", "latin_unchanged", "Rajshahi University", "Rajshahi University"),
    ]
    result = scores(evaluate(cases))
    assert (result["all"].correct, result["all"].total) == (2, 3)
    assert result["bijoy_converted"].accuracy == 0.5
    assert result["latin_unchanged"].accuracy == 1.0


def test_unfinished_labels_are_refused(write_csv):
    sheet = write_csv(
        "eval.csv",
        "id,group,file,row,column,original,pipeline_output,correct,expected,notes\n"
        "1,latin_unchanged,f.csv,2,1,Rajshahi,Rajshahi,,,\n"
        "2,latin_unchanged,f.csv,3,1,Dhaka,Dhaka,N,,\n",
    )
    with pytest.raises(LabelError, match="2 rows need labelling"):
        load_cases(sheet)


def test_non_utf8_sheet_gets_a_clear_message(tmp_path):
    sheet = tmp_path / "eval.csv"
    sheet.write_bytes("id,group,original\n1,x,café\n".encode("mac_roman"))
    with pytest.raises(LabelError, match="not saved as UTF-8"):
        load_cases(sheet)
