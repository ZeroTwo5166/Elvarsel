import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

from elvarsel import clean, fetch

ROOT = Path(__file__).parent.parent
FIXTURES = Path(__file__).parent / "fixtures"


def prices(times: list[str], eur: list[float], dkk: list[float]) -> pd.DataFrame:
    index = pd.DatetimeIndex(pd.to_datetime(times, utc=True), name="time_utc")
    return pd.DataFrame({"price_eur": eur, "price_dkk": dkk}, index=index)


def fixture_clean(tmp_path: Path, monkeypatch) -> pd.DataFrame:
    shutil.copytree(FIXTURES, tmp_path / fetch.FIXTURES_RAW_DIR)
    monkeypatch.chdir(tmp_path)
    return clean.clean(fetch.FIXTURES_RAW_DIR)


def test_fixture_transition_days_have_25_hours(tmp_path, monkeypatch):
    df = fixture_clean(tmp_path, monkeypatch)

    rows_by_local_date = df["time_dk"].dt.strftime("%Y-%m-%d").value_counts()
    assert rows_by_local_date["2024-10-27"] == 25
    assert rows_by_local_date["2025-10-26"] == 25
    local_month = df["time_dk"].dt.strftime("%Y-%m")
    assert df.loc[local_month == "2024-10", "price_eur"].notna().all()
    # The October 2025 fixture only covers 2025-10-26; earlier days are reindexed NaN.
    covered = df["time_dk"].dt.strftime("%Y-%m-%d") == "2025-10-26"
    assert df.loc[covered, "price_eur"].notna().all()


def test_repeated_local_hour_has_distinct_utc_times(tmp_path, monkeypatch):
    df = fixture_clean(tmp_path, monkeypatch)

    local = df["time_dk"].dt.strftime("%Y-%m-%d %H")
    repeated = df.index[local == "2024-10-27 02"]
    assert list(repeated) == [
        pd.Timestamp("2024-10-27T00:00", tz="UTC"),
        pd.Timestamp("2024-10-27T01:00", tz="UTC"),
    ]


def test_four_quarter_hours_average_to_one_hour():
    quarters = prices(
        [
            "2025-10-01T00:00",
            "2025-10-01T00:15",
            "2025-10-01T00:30",
            "2025-10-01T00:45",
        ],
        [1.0, 2.0, 3.0, 6.0],
        [10.0, 20.0, 30.0, 40.0],
    )

    hours = clean.to_hourly(quarters, periods_per_hour=4)

    assert hours.to_dict("index") == {
        pd.Timestamp("2025-10-01T00:00", tz="UTC"): {
            "price_eur": 3.0,
            "price_dkk": 25.0,
        }
    }


def test_incomplete_hour_has_nan_prices():
    quarters = prices(
        [
            "2025-10-01T00:00",
            "2025-10-01T00:15",
            "2025-10-01T00:30",
            "2025-10-01T00:45",
            "2025-10-01T01:00",
            "2025-10-01T01:15",
            "2025-10-01T01:30",
        ],
        [1.0, 2.0, 3.0, 6.0, 1.0, 2.0, 3.0],
        [10.0, 20.0, 30.0, 40.0, 10.0, 20.0, 30.0],
    )

    hours = clean.to_hourly(quarters, periods_per_hour=4)

    assert hours.loc["2025-10-01T00:00", clean.PRICES].tolist() == [3.0, 25.0]
    assert hours.loc["2025-10-01T01:00", clean.PRICES].isna().all()


def test_duplicate_time_keeps_first_frame():
    first = prices(["2025-09-30T22:00"], [1.0], [10.0])
    second = prices(["2025-09-30T22:00", "2025-09-30T23:00"], [2.0, 3.0], [20.0, 30.0])

    df = clean.combine([first, second])

    assert df["price_eur"].tolist() == [1.0, 3.0]
    assert df["price_dkk"].tolist() == [10.0, 30.0]


def test_long_overlap_keeps_first_frame_for_every_hour():
    hours = pd.date_range("2020-01-01", periods=50000, freq="h", tz="UTC")
    first = pd.DataFrame(
        {"price_eur": 1.0, "price_dkk": 10.0}, index=hours[:30000].rename("time_utc")
    )
    second = pd.DataFrame(
        {"price_eur": 2.0, "price_dkk": 20.0}, index=hours[20000:].rename("time_utc")
    )

    df = clean.combine([first, second])

    assert len(df) == 50000
    assert (df.loc[hours[20000] : hours[29999], "price_eur"] == 1.0).all()
    assert (df.loc[hours[30000] :, "price_eur"] == 2.0).all()


def test_missing_hour_is_reindexed_with_nan():
    df = clean.combine(
        [prices(["2025-10-01T00:00", "2025-10-01T02:00"], [1.0, 3.0], [10.0, 30.0])]
    )

    assert df.index.equals(
        pd.date_range("2025-10-01T00:00", periods=3, freq="h", tz="UTC")
    )
    assert df.loc["2025-10-01T01:00", clean.PRICES].isna().all()


def test_combined_index_is_unique_sorted_utc():
    later = prices(["2025-10-01T02:00", "2025-10-01T01:00"], [3.0, 2.0], [30.0, 20.0])
    earlier = prices(["2025-10-01T00:00", "2025-10-01T01:00"], [1.0, 9.0], [10.0, 90.0])

    df = clean.combine([later, earlier])

    assert df.index.is_unique
    assert df.index.is_monotonic_increasing
    assert str(df.index.tz) == "UTC"
    assert df.index.name == "time_utc"
    assert str(df["time_dk"].dt.tz) == clean.LOCAL_TZ


def test_script_writes_clean_table_from_fixture_dir(tmp_path):
    shutil.copytree(FIXTURES, tmp_path / fetch.FIXTURES_RAW_DIR)
    script = ROOT / "scripts" / "clean.py"

    subprocess.run(
        [sys.executable, str(script), "--fixtures"], cwd=tmp_path, check=True
    )

    table = (tmp_path / clean.FIXTURES_CLEAN_PATH).read_text(encoding="utf-8")
    assert table.startswith("time_utc,price_eur,price_dkk,time_dk\n")
    assert not (tmp_path / clean.CLEAN_PATH).exists()
