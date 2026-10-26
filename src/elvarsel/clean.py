import argparse
from pathlib import Path

import pandas as pd

from elvarsel.fetch import DATASETS, FIXTURES_RAW_DIR, RAW_DIR, Dataset
from elvarsel.gap_report import PRICE_COLUMNS, read_dataset

CLEAN_PATH = Path("data/clean/dk2_hourly.csv")
FIXTURES_CLEAN_PATH = Path("data/fixtures/clean/dk2_hourly.csv")
LOCAL_TZ = "Europe/Copenhagen"
PRICES = ["price_eur", "price_dkk"]


def load_prices(raw_dir: Path, dataset: Dataset) -> pd.DataFrame:
    rows = pd.DataFrame(read_dataset(raw_dir, dataset))
    eur, dkk = PRICE_COLUMNS[dataset.name]
    prices = pd.DataFrame(
        {
            "time_utc": pd.to_datetime(rows[dataset.utc_column], utc=True),
            "price_eur": pd.to_numeric(rows[eur]),
            "price_dkk": pd.to_numeric(rows[dkk]),
        }
    )
    return prices.set_index("time_utc").sort_index()


def to_hourly(prices: pd.DataFrame, periods_per_hour: int) -> pd.DataFrame:
    if periods_per_hour == 1:
        return prices
    grouped = prices.groupby(prices.index.floor("h"))
    hours = grouped.mean()
    hours.loc[grouped.size() != periods_per_hour, PRICES] = float("nan")
    hours.index.name = "time_utc"
    return hours


def combine(frames: list[pd.DataFrame]) -> pd.DataFrame:
    df = pd.concat(frames).sort_index(kind="stable")
    df = df[~df.index.duplicated(keep="first")]
    full = pd.date_range(
        df.index.min(), df.index.max(), freq="h", tz="UTC", name="time_utc"
    )
    df = df.reindex(full)
    df["time_dk"] = df.index.tz_convert(LOCAL_TZ)
    return df


def clean(raw_dir: Path) -> pd.DataFrame:
    frames = [
        to_hourly(load_prices(raw_dir, dataset), dataset.periods_per_hour)
        for dataset in DATASETS
    ]
    return combine(frames)


def write_clean(raw_dir: Path, path: Path) -> pd.DataFrame:
    df = clean(raw_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, lineterminator="\n")
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the hourly DK2 price table.")
    parser.add_argument(
        "--fixtures", action="store_true", help="read data/fixtures/raw"
    )
    args = parser.parse_args()
    if args.fixtures:
        raw_dir, path = FIXTURES_RAW_DIR, FIXTURES_CLEAN_PATH
    else:
        raw_dir, path = RAW_DIR, CLEAN_PATH
    write_clean(raw_dir, path)
    print(f"{path} written from {raw_dir}")


if __name__ == "__main__":
    main()
