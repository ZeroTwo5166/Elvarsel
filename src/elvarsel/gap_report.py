import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import pairwise
from pathlib import Path

from elvarsel.fetch import DATASETS, FIXTURES_RAW_DIR, RAW_DIR, Dataset, read_rows

REPORT_PATH = Path("reports/raw-data-gaps.md")
FIXTURES_REPORT_PATH = Path("reports/fixtures/raw-data-gaps.md")
PRICE_COLUMNS = {
    "Elspotprices": ("SpotPriceEUR", "SpotPriceDKK"),
    "DayAheadPrices": ("DayAheadPriceEUR", "DayAheadPriceDKK"),
}
# Local-date row counts verified against the API in docs/decisions.md.
DST_DAYS = (
    ("2024-03-31", "Elspotprices", 23),
    ("2024-10-27", "Elspotprices", 25),
    ("2025-10-26", "DayAheadPrices", 100),
    ("2026-03-29", "DayAheadPrices", 92),
)


@dataclass(frozen=True)
class Gap:
    start: datetime
    end: datetime
    intervals: int
    length: timedelta


@dataclass(frozen=True)
class DatasetGaps:
    dataset: Dataset
    rows: int
    first: datetime
    last: datetime
    duplicates: dict[datetime, int]
    gaps: list[Gap]
    null_prices: dict[str, int]
    dk2_rows_by_local_date: Counter


def read_dataset(raw_dir: Path, dataset: Dataset) -> list[dict]:
    rows = []
    for path in sorted((raw_dir / dataset.name).glob("*.csv")):
        rows += read_rows(path)
    return rows


def find_gaps(times: list[datetime], step: timedelta) -> list[Gap]:
    """Gaps between sorted unique times; end is the next time present."""
    gaps = []
    for previous, current in pairwise(times):
        if current - previous > step:
            start = previous + step
            gaps.append(Gap(start, current, (current - start) // step, current - start))
    return gaps


def dataset_gaps(dataset: Dataset, rows: list[dict]) -> DatasetGaps:
    keys = Counter(datetime.fromisoformat(row[dataset.utc_column]) for row in rows)
    times = sorted(keys)
    step = timedelta(hours=1) / dataset.periods_per_hour
    return DatasetGaps(
        dataset=dataset,
        rows=len(rows),
        first=times[0],
        last=times[-1],
        duplicates={time: count for time, count in keys.items() if count > 1},
        gaps=find_gaps(times, step),
        null_prices={
            column: sum(row[column] == "" for row in rows)
            for column in PRICE_COLUMNS[dataset.name]
        },
        dk2_rows_by_local_date=Counter(
            row[dataset.local_column][:10] for row in rows if row["PriceArea"] == "DK2"
        ),
    )


def markdown_table(header: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + " --- |" * len(header)]
    lines += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return "\n".join(lines)


def timestamp(time: datetime) -> str:
    return time.isoformat(timespec="minutes")


def report_markdown(results: list[DatasetGaps]) -> str:
    summary = markdown_table(
        [
            "dataset",
            "key",
            "rows",
            "first",
            "last",
            "duplicate keys",
            "missing intervals",
            "null EUR prices",
            "null DKK prices",
        ],
        [
            [
                result.dataset.name,
                result.dataset.utc_column,
                result.rows,
                timestamp(result.first),
                timestamp(result.last),
                len(result.duplicates),
                sum(gap.intervals for gap in result.gaps),
                *result.null_prices.values(),
            ]
            for result in results
        ],
    )
    duplicates = markdown_table(
        ["dataset", "duplicate key", "rows"],
        [
            [result.dataset.name, timestamp(time), count]
            for result in results
            for time, count in sorted(result.duplicates.items())
        ],
    )
    gaps = markdown_table(
        [
            "dataset",
            "gap start",
            "gap end (next present)",
            "missing intervals",
            "length",
        ],
        [
            [
                result.dataset.name,
                timestamp(gap.start),
                timestamp(gap.end),
                gap.intervals,
                gap.length,
            ]
            for result in results
            for gap in result.gaps
        ],
    )
    by_name = {result.dataset.name: result for result in results}
    dst = markdown_table(
        ["local date", "dataset", "DK2 rows", "expected (decisions.md)"],
        [
            [day, name, by_name[name].dk2_rows_by_local_date[day], expected]
            for day, name, expected in DST_DAYS
        ],
    )
    return "\n\n".join([summary, duplicates, gaps, dst]) + "\n"


def write_report(raw_dir: Path, path: Path) -> list[DatasetGaps]:
    results = [
        dataset_gaps(dataset, read_dataset(raw_dir, dataset)) for dataset in DATASETS
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report_markdown(results), encoding="utf-8")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Report gaps in the raw price data.")
    parser.add_argument("--fixtures", action="store_true", help="read fixture data")
    args = parser.parse_args()
    if args.fixtures:
        raw_dir, path = FIXTURES_RAW_DIR, FIXTURES_REPORT_PATH
    else:
        raw_dir, path = RAW_DIR, REPORT_PATH
    write_report(raw_dir, path)
    print(f"{path} written from {raw_dir}")
