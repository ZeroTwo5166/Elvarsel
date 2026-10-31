import math
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from elvarsel import clean, evaluate, features, fetch

ROOT = Path(__file__).parent.parent
FIXTURES = Path(__file__).parent / "fixtures"


def hourly(start: str, end: str) -> pd.DataFrame:
    index = pd.date_range(start, end, freq="h", tz="UTC", name="time_utc")
    price = 50 * np.sin(np.arange(len(index)) / 7) + np.arange(len(index)) / 100
    return pd.DataFrame({"price_eur": price}, index=index)


def local_times(index: pd.DatetimeIndex) -> list[str]:
    return list(index.tz_convert(clean.LOCAL_TZ).strftime("%Y-%m-%d %H:%M"))


@pytest.mark.parametrize(
    ("day", "periods", "first_utc"),
    [("2024-03-31", 23, "2024-03-30T23:00"), ("2024-10-27", 25, "2024-10-26T22:00")],
)
def test_split_boundary_on_dst_day_keeps_local_days_whole(day, periods, first_utc):
    index = hourly("2024-03-25", "2024-11-05").index
    next_day = str((pd.Timestamp(day) + pd.Timedelta(days=1)).date())

    before = index[evaluate.in_split(index, "2024-01-01", day)]
    on_day = index[evaluate.in_split(index, day, next_day)]

    assert len(on_day) == periods
    assert on_day[0] == pd.Timestamp(first_utc, tz="UTC")
    assert before[-1] == on_day[0] - pd.Timedelta(hours=1)
    assert local_times(before)[-1].endswith("23:00")
    assert local_times(on_day)[0] == f"{day} 00:00"
    assert local_times(on_day)[-1] == f"{day} 23:00"


def test_splits_do_not_overlap_and_cover_their_dates():
    index = hourly("2000-12-30", "2026-10-02").index
    masks = pd.DataFrame(
        {
            name: evaluate.in_split(index, *dates)
            for name, dates in evaluate.SPLITS.items()
        }
    )

    assert (masks.sum(axis=1) <= 1).all()
    for name, (start, end) in evaluate.SPLITS.items():
        rows = index[masks[name]]
        assert local_times(rows)[0] == f"{start} 00:00"
        last = pd.Timestamp(end) - pd.Timedelta(days=1)
        assert local_times(rows)[-1] == f"{last.date()} 23:00"
    ends = [end for _, end in evaluate.SPLITS.values()]
    starts = [start for start, _ in evaluate.SPLITS.values()]
    assert ends[:-1] == starts[1:]


def test_test_split_needs_explicit_flag():
    frame = hourly("2025-12-30", "2026-01-03")

    with pytest.raises(ValueError, match="held out"):
        evaluate.split_rows(frame, "test")
    rows = evaluate.split_rows(frame, "test", allow_test=True)
    assert local_times(rows.index)[0] == "2026-01-01 00:00"


def test_excluded_counts_hold_out_test_and_count_autumn_mask():
    frame = features.build_features(hourly("2024-12-20", "2026-01-05"))

    counts = evaluate.excluded_counts(frame)

    assert counts.loc["validation"].to_dict() == {
        "rows": 8760,
        "missing target": 0,
        "missing lag_24": 1,
        "missing lag_168": 0,
        "excluded": 1,
        "scored": 8759,
    }
    assert set(counts.loc["test"]) == {evaluate.HELD_OUT}


def test_metrics_on_hand_computed_errors():
    index = pd.date_range("2025-01-01", periods=4, freq="h", tz="UTC")
    errors = pd.DataFrame({"a": [1.0, -2.0, 3.0, 0.0]}, index=index)
    hour = pd.Series([0, 0, 1, 1], index=index)

    overall = evaluate.overall_scores(errors)
    by_hour = evaluate.scores_by(errors, hour)

    assert overall.loc["a", "rows"] == 4
    assert overall.loc["a", "MAE"] == 1.5
    assert math.isclose(overall.loc["a", "RMSE"], math.sqrt(3.5))
    assert by_hour["rows"].tolist() == [2, 2]
    assert by_hour["MAE a"].tolist() == [1.5, 1.5]
    assert np.allclose(by_hour["RMSE a"], [math.sqrt(2.5), math.sqrt(4.5)])


def test_extreme_scores_bands_and_shares():
    index = pd.date_range("2025-01-01", periods=4, freq="h", tz="UTC")
    errors = pd.DataFrame({"a": [1.0, -3.0, 2.0, 5.0]}, index=index)
    price = pd.Series([-5.0, 0.0, 50.0, evaluate.HIGH_PRICE_EUR + 1], index=index)

    table = evaluate.extreme_scores(errors, price)

    assert table["rows"].tolist() == [2, 1]
    assert table["share of scored rows (%)"].tolist() == [50.0, 25.0]
    assert table.loc[evaluate.LOW_BAND, "MAE a"] == 2.0
    assert math.isclose(table.loc[evaluate.LOW_BAND, "RMSE a"], math.sqrt(5))
    assert table.loc[evaluate.HIGH_BAND, "MAE a"] == 5.0


def test_baselines_share_rows_and_third_is_mean_of_first_two():
    index = pd.date_range("2025-01-01", periods=4, freq="h", tz="UTC")
    frame = pd.DataFrame(
        {
            "price_eur": [10.0, 20.0, 30.0, float("nan")],
            "lag_24": [12.0, 15.0, float("nan"), 1.0],
            "lag_168": [8.0, 25.0, 30.0, 1.0],
        },
        index=index,
    )

    errors = evaluate.baseline_errors(frame)

    assert errors.index.equals(index[:2])
    assert errors.notna().all().all()
    assert errors["persistence_24"].tolist() == [2.0, -5.0]
    assert errors["persistence_168"].tolist() == [-2.0, 5.0]
    assert errors["mean_24_168"].tolist() == [0.0, 0.0]
    pd.testing.assert_series_equal(
        errors["mean_24_168"],
        (errors["persistence_24"] + errors["persistence_168"]) / 2,
        check_names=False,
    )


def test_script_writes_fixture_report_only_to_fixture_path(tmp_path):
    shutil.copytree(FIXTURES, tmp_path / fetch.FIXTURES_RAW_DIR)

    for name in ["clean.py", "features.py", "evaluate.py"]:
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / name), "--fixtures"],
            cwd=tmp_path,
            check=True,
        )

    report = (tmp_path / evaluate.FIXTURES_REPORT_PATH).read_text(encoding="utf-8")
    assert not (tmp_path / evaluate.REPORT_PATH).exists()
    assert "| test | held out | held out |" in report
    for title in ["Overall", "By local hour of day", "By local month"]:
        assert f"## {title}" in report
