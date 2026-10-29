import math
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from elvarsel import clean, features, fetch

ROOT = Path(__file__).parent.parent
FIXTURES = Path(__file__).parent / "fixtures"
HOUR = pd.Timedelta(hours=1)
SOURCE_HOURS = {f"lag_{hours}": hours for hours in features.LAG_HOURS} | {
    "roll_mean_168": 24,
    "roll_std_168": 24,
}


def hourly(start: str, end: str) -> pd.DataFrame:
    index = pd.date_range(start, end, freq="h", tz="UTC", name="time_utc")
    price = 50 * np.sin(np.arange(len(index)) / 7) + np.arange(len(index)) / 100
    return pd.DataFrame({"price_eur": price}, index=index)


def local_dates(index: pd.DatetimeIndex) -> pd.Index:
    return pd.Index(index.tz_convert(clean.LOCAL_TZ).strftime("%Y-%m-%d"))


def fixture_features(tmp_path: Path, monkeypatch) -> pd.DataFrame:
    shutil.copytree(FIXTURES, tmp_path / fetch.FIXTURES_RAW_DIR)
    monkeypatch.chdir(tmp_path)
    return features.build_features(clean.clean(fetch.FIXTURES_RAW_DIR))


def assert_lag_is_elapsed_hours(df: pd.DataFrame, date: str, hours: int) -> None:
    day = df[local_dates(df.index) == date]
    for time, lag in day[f"lag_{hours}"].items():
        if not math.isnan(lag):
            assert lag == df.loc[time - hours * HOUR, "price_eur"]


def test_spring_day_lags_point_to_elapsed_utc_hours():
    df = features.build_features(hourly("2024-03-10", "2024-04-10"))

    day = df[local_dates(df.index) == "2024-03-31"]
    assert len(day) == 23
    assert day[["lag_24", "lag_168"]].notna().all().all()
    assert_lag_is_elapsed_hours(df, "2024-03-31", 24)
    assert_lag_is_elapsed_hours(df, "2024-03-31", 168)


def test_fixture_autumn_day_lags_point_to_elapsed_utc_hours(tmp_path, monkeypatch):
    df = fixture_features(tmp_path, monkeypatch)

    day = df[local_dates(df.index) == "2024-10-27"]
    assert len(day) == 25
    assert day["lag_168"].notna().all()
    assert_lag_is_elapsed_hours(df, "2024-10-27", 24)
    assert_lag_is_elapsed_hours(df, "2024-10-27", 168)


def test_fixture_autumn_last_period_masks_same_day_sources(tmp_path, monkeypatch):
    df = fixture_features(tmp_path, monkeypatch)

    day = df[local_dates(df.index) == "2024-10-27"]
    last = day["time_dk"].dt.hour == 23
    assert last.sum() == 1
    for column in ["lag_24", "roll_mean_168", "roll_std_168"]:
        assert day[column].isna().equals(last)
    longer_lags = ["lag_48", "lag_72", "lag_168", "lag_336"]
    assert day.loc[~last, longer_lags].notna().all().all()


def test_every_source_is_on_an_earlier_local_day_for_a_year():
    df = features.build_features(hourly("2023-12-01", "2025-01-01"))
    year = df[df.index.tz_convert(clean.LOCAL_TZ).year == 2024]
    target_dates = local_dates(year.index)

    for column, hours in SOURCE_HOURS.items():
        source_dates = local_dates(year.index - hours * HOUR)
        known = year[column].notna().to_numpy()
        assert known.sum() >= len(year) - 1
        assert (source_dates[known] < target_dates[known]).all()


def test_rolling_window_covers_168_hours_ending_24_hours_before():
    frame = hourly("2024-01-01", "2024-01-25")
    frame.loc["2024-01-15T05:00", "price_eur"] = float("nan")
    price = frame["price_eur"]

    df = features.build_features(frame)

    for time, row in df.iterrows():
        window = price.loc[time - 191 * HOUR : time - 24 * HOUR]
        if len(window) < 168 or window.isna().any():
            assert math.isnan(row["roll_mean_168"])
            assert math.isnan(row["roll_std_168"])
        else:
            assert len(window) == 168
            assert math.isclose(row["roll_mean_168"], window.mean())
            assert math.isclose(row["roll_std_168"], window.std(ddof=1))
    assert df["roll_mean_168"].notna().sum() > 0


def test_gaps_only_affect_lags_and_windows_that_include_them():
    full = hourly("2024-01-01", "2024-02-15")
    missing = pd.Timestamp("2024-01-10T05:00", tz="UTC")
    blank = pd.Timestamp("2024-01-12T17:00", tz="UTC")
    gapped = full.drop(missing)
    gapped.loc[blank, "price_eur"] = float("nan")

    expected = features.build_features(full)
    df = features.build_features(gapped)

    assert df.index.equals(expected.index)
    assert df.loc[[missing, blank], "price_eur"].isna().all()
    for column in expected.columns.drop("price_eur"):
        affected = np.zeros(len(df), dtype=bool)
        for gap in [missing, blank]:
            if column.startswith("lag_"):
                affected |= df.index == gap + SOURCE_HOURS[column] * HOUR
            elif column.startswith("roll_"):
                affected |= (df.index >= gap + 24 * HOUR) & (
                    df.index <= gap + 191 * HOUR
                )
        assert df.loc[affected, column].isna().all()
        pd.testing.assert_series_equal(
            df.loc[~affected, column], expected.loc[~affected, column]
        )


def test_reindexed_row_gets_local_time():
    frame = hourly("2024-06-30T20:00", "2024-06-30T23:00")
    frame["time_dk"] = frame.index.tz_convert(clean.LOCAL_TZ)
    missing = pd.Timestamp("2024-06-30T22:00", tz="UTC")

    df = features.build_features(frame.drop(missing))

    assert df.loc[missing, "time_dk"] == pd.Timestamp(
        "2024-07-01T00:00", tz=clean.LOCAL_TZ
    )


def test_calendar_hour_is_local_time():
    df = features.build_features(hourly("2024-01-01", "2025-01-01"))
    dates = local_dates(df.index)

    spring = df.loc[dates == "2024-03-31", "hour"]
    assert len(spring) == 23
    assert spring.nunique() == 23
    autumn = df.loc[dates == "2024-10-27", "hour"]
    assert len(autumn) == 25
    assert autumn.nunique() == 24
    assert (autumn == 2).sum() == 2
    midnight = df.loc[pd.Timestamp("2024-06-30T22:00", tz="UTC")]
    assert midnight[["hour", "day_of_week", "month"]].tolist() == [0, 0, 7]


def test_holiday_flags_use_danish_public_holidays():
    df = features.build_features(hourly("2024-01-01", "2025-01-01"))
    dates = local_dates(df.index)

    def flag(column: str, date: str) -> set[int]:
        return set(df.loc[dates == date, column])

    assert flag("is_holiday", "2024-12-25") == {1}
    assert flag("is_holiday", "2024-04-01") == {1}
    assert flag("is_holiday", "2024-06-05") == {0}
    assert flag("is_holiday", "2024-12-27") == {0}
    assert flag("is_day_after_holiday", "2024-12-26") == {1}
    assert flag("is_day_after_holiday", "2024-12-25") == {0}


def test_script_writes_feature_table_from_fixture_dir(tmp_path):
    shutil.copytree(FIXTURES, tmp_path / fetch.FIXTURES_RAW_DIR)

    for name in ["clean.py", "features.py"]:
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / name), "--fixtures"],
            cwd=tmp_path,
            check=True,
        )

    table = (tmp_path / features.FIXTURES_FEATURES_PATH).read_text(encoding="utf-8")
    assert table.startswith(
        "time_utc,price_eur,price_dkk,time_dk,lag_24,lag_48,lag_72,lag_168,lag_336,"
        "roll_mean_168,roll_std_168,hour,day_of_week,month,is_holiday,"
        "is_day_after_holiday\n"
    )
    assert not (tmp_path / features.FEATURES_PATH).exists()
