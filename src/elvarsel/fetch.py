import argparse
import calendar
import csv
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import groupby
from pathlib import Path

import requests

API_URL = "https://api.energidataservice.dk/dataset"
ATTEMPTS = 5
DEFAULT_RETRY_AFTER = 60
REQUEST_PAUSE = 1
RAW_DIR = Path("data/raw")
FIXTURES_RAW_DIR = Path("data/fixtures/raw")
FIXTURES_DIR = Path("tests/fixtures")


@dataclass(frozen=True)
class Dataset:
    name: str
    utc_column: str
    local_column: str
    periods_per_hour: int
    first_month: str
    last_month: str | None


DATASETS = (
    Dataset("Elspotprices", "HourUTC", "HourDK", 1, "2000-10", "2025-09"),
    Dataset("DayAheadPrices", "TimeUTC", "TimeDK", 4, "2025-10", None),
)


def month_arg(value: str) -> str:
    return datetime.strptime(value, "%Y-%m").strftime("%Y-%m")


def next_month(month: str) -> str:
    year, number = map(int, month.split("-"))
    if number == 12:
        return f"{year + 1:04d}-01"
    return f"{year:04d}-{number + 1:02d}"


def months_between(start: str, end: str) -> list[str]:
    months = []
    month = start
    while month <= end:
        months.append(month)
        month = next_month(month)
    return months


def last_complete_month() -> str:
    # UTC never runs ahead of Danish local time, so this never treats an
    # unfinished local month as complete.
    now = datetime.now(UTC)
    if now.month == 1:
        return f"{now.year - 1:04d}-12"
    return f"{now.year:04d}-{now.month - 1:02d}"


def expected_rows(dataset: Dataset, month: str) -> int:
    year, number = map(int, month.split("-"))
    days = calendar.monthrange(year, number)[1]
    return days * 24 * dataset.periods_per_hour


def check_row_count(dataset: Dataset, month: str, rows: int) -> None:
    """Raise if rows is not a full month, allowing one daylight-saving hour."""
    expected = expected_rows(dataset, month)
    tolerance = dataset.periods_per_hour
    if abs(rows - expected) > tolerance:
        raise ValueError(
            f"{dataset.name} {month}: {rows} rows, expected {expected} +/- {tolerance}"
        )


def get_with_retry(
    session: requests.Session, url: str, params: dict, label: str
) -> requests.Response:
    for attempt in range(1, ATTEMPTS + 1):
        wait = 2 ** (attempt - 1)
        try:
            response = session.get(url, params=params, timeout=60)
        except (requests.ConnectionError, requests.Timeout) as error:
            failure = error
        else:
            if response.status_code == 429:
                wait = int(response.headers.get("Retry-After", DEFAULT_RETRY_AFTER))
            elif response.status_code < 500:
                response.raise_for_status()
                return response
            failure = requests.HTTPError(
                f"{response.status_code} from {response.url}", response=response
            )
        if attempt < ATTEMPTS:
            time.sleep(wait)
    raise RuntimeError(f"{label}: failed after {ATTEMPTS} attempts") from failure


def request_records(
    session: requests.Session, dataset: Dataset, start: str, end: str, label: str
) -> list[dict]:
    params = {
        "start": start,
        "end": end,
        "filter": '{"PriceArea":"DK2"}',
        "sort": f"{dataset.utc_column} asc",
        "limit": 0,
    }
    response = get_with_retry(session, f"{API_URL}/{dataset.name}", params, label)
    body = response.json()
    records = body["records"]
    if body["total"] != len(records):
        raise ValueError(
            f"{label}: total is {body['total']} but {len(records)} rows received"
        )
    return records


def fetch_months(
    session: requests.Session, dataset: Dataset, months: list[str]
) -> dict[str, list[dict]]:
    """Fetch consecutive months in one request and split the rows by local month."""
    first, last = months[0], months[-1]
    label = (
        f"{dataset.name} {first}"
        if first == last
        else f"{dataset.name} {first}..{last}"
    )
    start = f"{first}-01"
    end = f"{next_month(last)}-01"
    rows_by_month = {month: [] for month in months}
    for record in request_records(session, dataset, start, end, label):
        rows_by_month[record[dataset.local_column][:7]].append(record)
    return rows_by_month


def months_by_year(months: list[str]) -> list[list[str]]:
    return [list(group) for _, group in groupby(months, key=lambda month: month[:4])]


def read_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write then rename, so an interrupted run never leaves a partial month
    # that later runs would skip.
    partial = path.with_suffix(".csv.partial")
    with partial.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    partial.replace(path)


def dataset_months(
    dataset: Dataset, start: str | None, end: str | None, fixtures_dir: Path | None
) -> list[str]:
    if fixtures_dir is None:
        last = dataset.last_month or last_complete_month()
        months = months_between(dataset.first_month, last)
    else:
        months = sorted(
            path.stem for path in (fixtures_dir / dataset.name).glob("*.csv")
        )
    return [
        month
        for month in months
        if (start is None or month >= start) and (end is None or month <= end)
    ]


def fetch_all(
    raw_dir: Path,
    start: str | None = None,
    end: str | None = None,
    force: bool = False,
    fixtures_dir: Path | None = None,
    session: requests.Session | None = None,
) -> None:
    """Write each dataset month to raw_dir/<dataset>/<YYYY-MM>.csv."""
    if fixtures_dir is None:
        last_complete = last_complete_month()
        if end is not None and end > last_complete:
            raise ValueError(
                f"{end} is not a complete month, the last one is {last_complete}"
            )
        session = session or requests.Session()
    fetched = False
    for dataset in DATASETS:
        months = dataset_months(dataset, start, end, fixtures_dir)
        for year in months_by_year(months):
            paths = {month: raw_dir / dataset.name / f"{month}.csv" for month in year}
            missing = [month for month in year if force or not paths[month].exists()]
            if missing and fixtures_dir is None:
                if fetched:
                    time.sleep(REQUEST_PAUSE)
                fetched = True
                rows_by_month = fetch_months(session, dataset, year)
            for month in year:
                if month not in missing:
                    rows = read_rows(paths[month])
                    print(f"{dataset.name} {month} {len(rows)} skipped")
                    continue
                if fixtures_dir is None:
                    rows = rows_by_month[month]
                    check_row_count(dataset, month, len(rows))
                else:
                    rows = read_rows(fixtures_dir / dataset.name / f"{month}.csv")
                write_rows(paths[month], rows)
                print(f"{dataset.name} {month} {len(rows)} written")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download DK2 day-ahead prices.")
    parser.add_argument("--start", type=month_arg, help="first month, YYYY-MM")
    parser.add_argument("--end", type=month_arg, help="last month, YYYY-MM")
    parser.add_argument("--force", action="store_true", help="refetch existing months")
    parser.add_argument("--fixtures", action="store_true", help="read tests/fixtures")
    args = parser.parse_args()
    if args.fixtures:
        fetch_all(FIXTURES_RAW_DIR, args.start, args.end, args.force, FIXTURES_DIR)
    else:
        fetch_all(RAW_DIR, args.start, args.end, args.force)


if __name__ == "__main__":
    main()
