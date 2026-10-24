import json
from pathlib import Path

import pytest
import requests

from elvarsel import fetch

FIXTURES = Path(__file__).parent / "fixtures"
SPOT, DAYAHEAD = fetch.DATASETS


def fake_response(
    status: int, body: dict | None = None, headers: dict | None = None
) -> requests.Response:
    response = requests.Response()
    response.status_code = status
    response.url = "https://api.energidataservice.dk/dataset/Elspotprices"
    response.headers.update(headers or {})
    response._content = json.dumps(body or {}).encode()
    return response


def records_response(rows_per_month: dict[str, int]) -> requests.Response:
    records = [
        {"HourUTC": str(row), "HourDK": f"{month}-01T00:00:00"}
        for month, rows in rows_per_month.items()
        for row in range(rows)
    ]
    return fake_response(200, {"total": len(records), "records": records})


def full_months(*months: str) -> dict[str, int]:
    return {month: fetch.expected_rows(SPOT, month) for month in months}


class FakeSession:
    def __init__(self, outcomes: list):
        self.outcomes = outcomes
        self.calls = 0
        self.ranges = []

    def get(self, url, params, timeout):
        outcome = self.outcomes[min(self.calls, len(self.outcomes) - 1)]
        self.calls += 1
        self.ranges.append((params["start"], params["end"]))
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


@pytest.fixture
def sleeps(monkeypatch):
    waits = []
    monkeypatch.setattr(fetch.time, "sleep", waits.append)
    return waits


def test_fixtures_mode_writes_expected_files(tmp_path):
    fetch.fetch_all(tmp_path, fixtures_dir=FIXTURES)

    written = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*.csv"))
    assert written == [
        Path("DayAheadPrices/2025-10.csv"),
        Path("Elspotprices/2024-10.csv"),
    ]
    for path in written:
        assert (tmp_path / path).read_bytes() == (FIXTURES / path).read_bytes()


def test_second_run_skips_existing_months(tmp_path, capsys):
    fetch.fetch_all(tmp_path, fixtures_dir=FIXTURES)
    capsys.readouterr()

    fetch.fetch_all(tmp_path, fixtures_dir=FIXTURES)

    lines = capsys.readouterr().out.splitlines()
    assert lines == [
        "Elspotprices 2024-10 745 skipped",
        "DayAheadPrices 2025-10 100 skipped",
    ]


def test_force_rewrites_existing_months(tmp_path, capsys):
    fetch.fetch_all(tmp_path, fixtures_dir=FIXTURES)
    capsys.readouterr()

    fetch.fetch_all(tmp_path, force=True, fixtures_dir=FIXTURES)

    assert all(
        line.endswith("written") for line in capsys.readouterr().out.split("\n")[:-1]
    )


def test_fixture_transition_days_have_extra_periods():
    spot = fetch.read_rows(FIXTURES / "Elspotprices" / "2024-10.csv")
    dayahead = fetch.read_rows(FIXTURES / "DayAheadPrices" / "2025-10.csv")

    assert sum(row["HourDK"].startswith("2024-10-27") for row in spot) == 25
    assert len(dayahead) == 100
    assert all(row["TimeDK"].startswith("2025-10-26") for row in dayahead)


@pytest.mark.parametrize(
    ("dataset", "month", "rows"),
    [(SPOT, "2024-10", 745), (SPOT, "2024-03", 743), (DAYAHEAD, "2025-10", 2980)],
)
def test_row_count_check_accepts_full_months(dataset, month, rows):
    fetch.check_row_count(dataset, month, rows)


@pytest.mark.parametrize(
    ("dataset", "month", "rows"),
    [(SPOT, "2024-10", 720), (SPOT, "2024-02", 744), (DAYAHEAD, "2025-10", 100)],
)
def test_row_count_check_rejects_short_or_long_months(dataset, month, rows):
    with pytest.raises(ValueError, match=f"{dataset.name} {month}"):
        fetch.check_row_count(dataset, month, rows)


def test_retries_server_errors_then_succeeds(sleeps):
    session = FakeSession(
        [
            fake_response(503),
            requests.ConnectionError("reset"),
            records_response({"2024-10": 745}),
        ]
    )

    rows_by_month = fetch.fetch_months(session, SPOT, ["2024-10"])

    assert len(rows_by_month["2024-10"]) == 745
    assert session.calls == 3
    assert sleeps == [1, 2]


def test_gives_up_after_five_attempts_naming_dataset_and_months(sleeps):
    session = FakeSession([fake_response(502)])

    with pytest.raises(RuntimeError, match="Elspotprices 2024-01..2024-12"):
        fetch.fetch_months(session, SPOT, fetch.months_between("2024-01", "2024-12"))
    assert session.calls == 5
    assert sleeps == [1, 2, 4, 8]


def test_does_not_retry_client_errors(sleeps):
    session = FakeSession([fake_response(400)])

    with pytest.raises(requests.HTTPError):
        fetch.fetch_months(session, SPOT, ["2024-10"])
    assert session.calls == 1
    assert sleeps == []


def test_rate_limit_waits_retry_after_then_succeeds(sleeps):
    session = FakeSession(
        [
            fake_response(429, headers={"Retry-After": "257"}),
            records_response({"2024-10": 745}),
        ]
    )

    rows_by_month = fetch.fetch_months(session, SPOT, ["2024-10"])

    assert len(rows_by_month["2024-10"]) == 745
    assert session.calls == 2
    assert sleeps == [257]


def test_rate_limit_without_retry_after_waits_default(sleeps):
    session = FakeSession([fake_response(429), records_response({"2024-10": 745})])

    fetch.fetch_months(session, SPOT, ["2024-10"])

    assert sleeps == [fetch.DEFAULT_RETRY_AFTER]


def test_rate_limit_counts_toward_five_attempts(sleeps):
    session = FakeSession([fake_response(429, headers={"Retry-After": "3"})])

    with pytest.raises(RuntimeError, match="Elspotprices 2024-10"):
        fetch.fetch_months(session, SPOT, ["2024-10"])
    assert session.calls == 5
    assert sleeps == [3, 3, 3, 3]


def test_rejects_response_with_missing_rows():
    session = FakeSession([fake_response(200, {"total": 2, "records": [{"a": 1}]})])

    with pytest.raises(ValueError, match="total is 2"):
        fetch.fetch_months(session, SPOT, ["2024-10"])


def test_fetch_months_splits_rows_by_local_month():
    months = fetch.months_between("2024-01", "2024-12")
    session = FakeSession([records_response(full_months(*months))])

    rows_by_month = fetch.fetch_months(session, SPOT, months)

    assert session.ranges == [("2024-01-01", "2025-01-01")]
    assert {month: len(rows) for month, rows in rows_by_month.items()} == (
        full_months(*months)
    )


def test_default_ranges_split_into_calendar_years():
    spot = fetch.months_by_year(fetch.dataset_months(SPOT, None, None, None))
    dayahead = fetch.months_by_year(fetch.dataset_months(DAYAHEAD, None, None, None))

    assert spot[0] == ["2000-10", "2000-11", "2000-12"]
    assert spot[-1] == fetch.months_between("2025-01", "2025-09")
    assert len(spot) == 26
    assert dayahead[0] == ["2025-10", "2025-11", "2025-12"]
    assert dayahead[-1][-1] == fetch.last_complete_month()
    assert all(len({month[:4] for month in year}) == 1 for year in spot + dayahead)


def test_one_request_per_year_with_pause_between(tmp_path, sleeps, capsys):
    session = FakeSession(
        [
            records_response(full_months("2024-11", "2024-12")),
            records_response(full_months("2025-01")),
        ]
    )

    fetch.fetch_all(tmp_path, start="2024-11", end="2025-01", session=session)

    assert session.ranges == [
        ("2024-11-01", "2025-01-01"),
        ("2025-01-01", "2025-02-01"),
    ]
    assert sleeps == [fetch.REQUEST_PAUSE]
    assert capsys.readouterr().out.splitlines() == [
        "Elspotprices 2024-11 720 written",
        "Elspotprices 2024-12 744 written",
        "Elspotprices 2025-01 744 written",
    ]
    assert sorted(path.name for path in tmp_path.rglob("*.csv")) == [
        "2024-11.csv",
        "2024-12.csv",
        "2025-01.csv",
    ]


def test_year_with_all_months_present_is_not_requested(tmp_path, capsys):
    for month in ("2024-11", "2024-12"):
        fetch.write_rows(tmp_path / "Elspotprices" / f"{month}.csv", [{"a": "1"}])
    session = FakeSession([records_response(full_months("2025-01"))])

    fetch.fetch_all(tmp_path, start="2024-11", end="2025-01", session=session)

    assert session.ranges == [("2025-01-01", "2025-02-01")]
    assert capsys.readouterr().out.splitlines() == [
        "Elspotprices 2024-11 1 skipped",
        "Elspotprices 2024-12 1 skipped",
        "Elspotprices 2025-01 744 written",
    ]


def test_existing_month_in_requested_year_is_kept(tmp_path, capsys):
    existing = tmp_path / "Elspotprices" / "2024-11.csv"
    fetch.write_rows(existing, [{"a": "1"}])
    before = existing.read_bytes()
    session = FakeSession([records_response(full_months("2024-11", "2024-12"))])

    fetch.fetch_all(tmp_path, start="2024-11", end="2024-12", session=session)

    assert session.ranges == [("2024-11-01", "2025-01-01")]
    assert existing.read_bytes() == before
    assert capsys.readouterr().out.splitlines() == [
        "Elspotprices 2024-11 1 skipped",
        "Elspotprices 2024-12 744 written",
    ]


def test_short_month_inside_a_year_fails_naming_the_month(tmp_path):
    rows = full_months("2024-11", "2024-12") | {"2024-12": 700}
    session = FakeSession([records_response(rows)])

    with pytest.raises(ValueError, match="Elspotprices 2024-12: 700 rows"):
        fetch.fetch_all(tmp_path, start="2024-11", end="2024-12", session=session)
    assert not (tmp_path / "Elspotprices" / "2024-12.csv").exists()


def test_unfinished_month_is_refused(tmp_path):
    session = FakeSession([AssertionError("network must not be called")])

    with pytest.raises(ValueError, match="not a complete month"):
        fetch.fetch_all(tmp_path, start="2999-01", end="2999-01", session=session)
    assert session.calls == 0
