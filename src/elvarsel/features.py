import argparse
from pathlib import Path

import holidays
import pandas as pd

from elvarsel.clean import CLEAN_PATH, FIXTURES_CLEAN_PATH, LOCAL_TZ

FEATURES_PATH = Path("data/features/dk2_hourly.csv")
FIXTURES_FEATURES_PATH = Path("data/fixtures/features/dk2_hourly.csv")
TARGET = "price_eur"
LAG_HOURS = (24, 48, 72, 168, 336)
WINDOW_HOURS = 168
WINDOW_END_HOURS = 24


def complete_hourly(frame: pd.DataFrame) -> pd.DataFrame:
    full = pd.date_range(
        frame.index.min(), frame.index.max(), freq="h", tz="UTC", name="time_utc"
    )
    df = frame.reindex(full)
    if "time_dk" in df.columns:
        df["time_dk"] = df.index.tz_convert(LOCAL_TZ)
    return df


def price_hours_before(price: pd.Series, hours: int) -> pd.Series:
    values = price.reindex(price.index - pd.Timedelta(hours=hours)).to_numpy()
    return pd.Series(values, index=price.index)


def source_on_earlier_day(index: pd.DatetimeIndex, hours: int) -> pd.Series:
    # On the 25-hour autumn day, 24 elapsed hours before the last period is the
    # first period of the same delivery day, whose price is not known at cutoff.
    target_day = index.tz_convert(LOCAL_TZ).normalize()
    source_day = (index - pd.Timedelta(hours=hours)).tz_convert(LOCAL_TZ).normalize()
    return pd.Series(source_day < target_day, index=index)


def lag_features(price: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {
            f"lag_{hours}": price_hours_before(price, hours).where(
                source_on_earlier_day(price.index, hours)
            )
            for hours in LAG_HOURS
        }
    )


def rolling_features(price: pd.Series) -> pd.DataFrame:
    window = price_hours_before(price, WINDOW_END_HOURS).rolling(
        f"{WINDOW_HOURS}h", min_periods=WINDOW_HOURS
    )
    stats = pd.DataFrame(
        {
            f"roll_mean_{WINDOW_HOURS}": window.mean(),
            f"roll_std_{WINDOW_HOURS}": window.std(),
        }
    )
    return stats.where(source_on_earlier_day(price.index, WINDOW_END_HOURS), axis=0)


def calendar_features(index: pd.DatetimeIndex) -> pd.DataFrame:
    local = index.tz_convert(LOCAL_TZ)
    day = local.tz_localize(None).normalize()
    years = range(int(day.year.min()) - 1, int(day.year.max()) + 1)
    public = pd.to_datetime(
        list(holidays.country_holidays("DK", years=years, categories=holidays.PUBLIC))
    )
    return pd.DataFrame(
        {
            "hour": local.hour,
            "day_of_week": local.day_of_week,
            "month": local.month,
            "is_holiday": day.isin(public).astype(int),
            "is_day_after_holiday": (day - pd.Timedelta(days=1))
            .isin(public)
            .astype(int),
        },
        index=index,
    )


def build_features(frame: pd.DataFrame) -> pd.DataFrame:
    df = complete_hourly(frame)
    price = df[TARGET]
    return pd.concat(
        [
            df,
            lag_features(price),
            rolling_features(price),
            calendar_features(df.index),
        ],
        axis=1,
    )


def write_features(clean_path: Path, path: Path) -> pd.DataFrame:
    frame = pd.read_csv(clean_path, index_col="time_utc", parse_dates=["time_utc"])
    df = build_features(frame)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, lineterminator="\n")
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the DK2 feature table.")
    parser.add_argument(
        "--fixtures", action="store_true", help="read data/fixtures/clean"
    )
    args = parser.parse_args()
    if args.fixtures:
        clean_path, path = FIXTURES_CLEAN_PATH, FIXTURES_FEATURES_PATH
    else:
        clean_path, path = CLEAN_PATH, FEATURES_PATH
    write_features(clean_path, path)
    print(f"{path} written from {clean_path}")


if __name__ == "__main__":
    main()
