import argparse
import math
from numbers import Integral
from pathlib import Path

import pandas as pd

from elvarsel.baselines import INPUTS, baseline_predictions
from elvarsel.clean import LOCAL_TZ
from elvarsel.features import FEATURES_PATH, FIXTURES_FEATURES_PATH, TARGET

REPORT_PATH = Path("reports/baselines-validation.md")
FIXTURES_REPORT_PATH = Path("reports/fixtures/baselines-validation.md")
SPLITS = {
    "train": ("2001-01-01", "2025-01-01"),
    "validation": ("2025-01-01", "2026-01-01"),
    "test": ("2026-01-01", "2026-10-01"),
}
TEST_SPLIT = "test"
# 95th percentile of price_eur over the train split, 2001-2024.
HIGH_PRICE_EUR = 124.93
LOW_BAND = "at or below 0"
HIGH_BAND = f"above {HIGH_PRICE_EUR}"
HELD_OUT = "held out"


def delivery_day(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return index.tz_convert(LOCAL_TZ).tz_localize(None).normalize()


def in_split(index: pd.DatetimeIndex, start: str, end: str) -> pd.Series:
    day = delivery_day(index)
    return pd.Series((day >= start) & (day < end), index=index)


def split_rows(
    frame: pd.DataFrame, name: str, allow_test: bool = False
) -> pd.DataFrame:
    if name == TEST_SPLIT and not allow_test:
        raise ValueError("test split is held out; allow_test is for the final run")
    return frame[in_split(frame.index, *SPLITS[name])]


def scored_rows(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.dropna(subset=[TARGET, *INPUTS])


def baseline_errors(frame: pd.DataFrame) -> pd.DataFrame:
    rows = scored_rows(frame)
    return baseline_predictions(rows).sub(rows[TARGET], axis=0)


def mae(errors: pd.DataFrame) -> pd.Series:
    return errors.abs().mean()


def rmse(errors: pd.DataFrame) -> pd.Series:
    return (errors**2).mean() ** 0.5


def overall_scores(errors: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {"rows": errors.count(), "MAE": mae(errors), "RMSE": rmse(errors)}
    )


def scores_by(errors: pd.DataFrame, key: pd.Series) -> pd.DataFrame:
    table = pd.concat(
        {
            "MAE": errors.abs().groupby(key).mean(),
            "RMSE": (errors**2).groupby(key).mean() ** 0.5,
        },
        axis=1,
    )
    table.columns = [f"{metric} {name}" for metric, name in table.columns]
    table.insert(0, "rows", errors.groupby(key).size())
    return table


def price_band(price: pd.Series) -> pd.Series:
    band = pd.Series(None, index=price.index, dtype="object")
    band[price <= 0] = LOW_BAND
    band[price > HIGH_PRICE_EUR] = HIGH_BAND
    return band


def extreme_scores(errors: pd.DataFrame, price: pd.Series) -> pd.DataFrame:
    table = scores_by(errors, price_band(price)).reindex([LOW_BAND, HIGH_BAND])
    table["rows"] = table["rows"].fillna(0).astype(int)
    table.insert(1, "share of scored rows (%)", 100 * table["rows"] / len(errors))
    return table


def excluded_counts(frame: pd.DataFrame) -> pd.DataFrame:
    counts = {}
    for name in SPLITS:
        if name == TEST_SPLIT:
            counts[name] = dict.fromkeys(counts["train"], HELD_OUT)
            continue
        part = split_rows(frame, name)
        excluded = len(part) - len(scored_rows(part))
        counts[name] = {
            "rows": len(part),
            "missing target": int(part[TARGET].isna().sum()),
            **{f"missing {lag}": int(part[lag].isna().sum()) for lag in INPUTS},
            "excluded": excluded,
            "scored": len(part) - excluded,
        }
    return pd.DataFrame.from_dict(counts, orient="index", dtype="object")


def format_cell(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Integral):
        return str(value)
    if math.isnan(value):
        return "n/a"
    return f"{value:.2f}"


def markdown_table(table: pd.DataFrame, index_name: str) -> str:
    header = [index_name, *table.columns]
    lines = [
        "| " + " | ".join(header) + " |",
        "|" + "---|" * len(header),
    ]
    for label, *values in table.itertuples(name=None):
        cells = [str(label), *map(format_cell, values)]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def validation_report(frame: pd.DataFrame) -> str:
    validation = split_rows(frame, "validation")
    errors = baseline_errors(validation)
    rows = validation.loc[errors.index]
    sections = [
        ("Overall", markdown_table(overall_scores(errors), "baseline")),
        (
            "By local hour of day",
            markdown_table(scores_by(errors, rows["hour"]), "hour"),
        ),
        ("By local month", markdown_table(scores_by(errors, rows["month"]), "month")),
        (
            f"Extreme prices, high threshold {HIGH_PRICE_EUR} EUR/MWh (train p95)",
            markdown_table(extreme_scores(errors, rows[TARGET]), "band"),
        ),
        (
            "Rows excluded for missing target or lags",
            markdown_table(excluded_counts(frame), "split"),
        ),
    ]
    text = [
        "# Baselines on validation (2025)",
        "",
        "EUR/MWh. All three baselines are scored on the same rows. Lags are "
        "elapsed UTC hours; hour and month are local time.",
    ]
    for title, table in sections:
        text += ["", f"## {title}", "", table]
    return "\n".join(text) + "\n"


def write_report(features_path: Path, path: Path) -> str:
    frame = pd.read_csv(features_path, index_col="time_utc", parse_dates=["time_utc"])
    frame = frame[delivery_day(frame.index) < SPLITS[TEST_SPLIT][0]]
    report = validation_report(frame)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8", newline="\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Score the baselines on validation.")
    parser.add_argument(
        "--fixtures", action="store_true", help="read data/fixtures/features"
    )
    args = parser.parse_args()
    if args.fixtures:
        features_path, path = FIXTURES_FEATURES_PATH, FIXTURES_REPORT_PATH
    else:
        features_path, path = FEATURES_PATH, REPORT_PATH
    write_report(features_path, path)
    print(f"{path} written from {features_path}")


if __name__ == "__main__":
    main()
