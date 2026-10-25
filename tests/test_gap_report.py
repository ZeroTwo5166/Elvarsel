import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from elvarsel import fetch, gap_report

ROOT = Path(__file__).parent.parent
FIXTURES = Path(__file__).parent / "fixtures"
SPOT, DAYAHEAD = fetch.DATASETS


def test_fixture_months_have_no_gaps_or_duplicates(tmp_path):
    results = gap_report.write_report(FIXTURES, tmp_path / "gaps.md")

    for result in results:
        assert result.gaps == []
        assert result.duplicates == {}
    spot, dayahead = results
    assert (spot.rows, timestamp_pair(spot)) == (
        745,
        ("2024-09-30T22:00", "2024-10-31T22:00"),
    )
    assert (dayahead.rows, timestamp_pair(dayahead)) == (
        100,
        ("2025-10-25T22:00", "2025-10-26T22:45"),
    )


def test_fixture_transition_days_have_25_and_100_rows(tmp_path):
    spot, dayahead = gap_report.write_report(FIXTURES, tmp_path / "gaps.md")

    assert spot.dk2_rows_by_local_date["2024-10-27"] == 25
    assert dayahead.dk2_rows_by_local_date["2025-10-26"] == 100
    report = (tmp_path / "gaps.md").read_text(encoding="utf-8")
    assert "| 2024-10-27 | Elspotprices | 25 | 25 |" in report
    assert "| 2025-10-26 | DayAheadPrices | 100 | 100 |" in report


def test_missing_hours_and_repeated_keys_are_reported():
    times = ["2024-10-01T00:00:00", "2024-10-01T01:00:00", "2024-10-01T04:00:00"]
    rows = [
        {
            "HourUTC": time,
            "HourDK": time,
            "PriceArea": "DK2",
            "SpotPriceEUR": "1",
            "SpotPriceDKK": "",
        }
        for time in [*times, times[1]]
    ]

    result = gap_report.dataset_gaps(SPOT, rows)

    assert result.gaps == [
        gap_report.Gap(
            datetime(2024, 10, 1, 2), datetime(2024, 10, 1, 4), 2, timedelta(hours=2)
        )
    ]
    assert result.duplicates == {datetime(2024, 10, 1, 1): 2}
    assert result.null_prices == {"SpotPriceEUR": 0, "SpotPriceDKK": 4}


def test_quarter_hour_gap_is_counted_in_intervals():
    times = [datetime(2025, 10, 1, 0, 0), datetime(2025, 10, 1, 1, 0)]

    gaps = gap_report.find_gaps(times, timedelta(minutes=15))

    assert [(gap.intervals, gap.length) for gap in gaps] == [(3, timedelta(minutes=45))]


def test_script_writes_report_from_fixture_dir(tmp_path):
    shutil.copytree(FIXTURES, tmp_path / fetch.FIXTURES_RAW_DIR)
    script = ROOT / "scripts" / "gap_report.py"

    subprocess.run(
        [sys.executable, str(script), "--fixtures"], cwd=tmp_path, check=True
    )

    report = (tmp_path / gap_report.FIXTURES_REPORT_PATH).read_text(encoding="utf-8")
    assert report.startswith("| dataset | key | rows |")
    assert "| Elspotprices | HourUTC | 745 |" in report
    assert not (tmp_path / gap_report.REPORT_PATH).exists()


def timestamp_pair(result: gap_report.DatasetGaps) -> tuple[str, str]:
    return gap_report.timestamp(result.first), gap_report.timestamp(result.last)
