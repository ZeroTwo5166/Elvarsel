import argparse
import math
from collections.abc import Callable, Mapping
from numbers import Integral
from pathlib import Path

import pandas as pd
from sklearn.pipeline import Pipeline

from elvarsel.baselines import INPUTS, baseline_predictions
from elvarsel.clean import LOCAL_TZ
from elvarsel.features import FEATURES_PATH, FIXTURES_FEATURES_PATH, TARGET
from elvarsel.models import (
    ALPHAS,
    HGB_GRID,
    MODEL_FEATURES,
    PRICE_FEATURES,
    fit_hgb,
    fit_ridge,
    hgb_predictions,
    ridge_coefficients,
    ridge_predictions,
)

REPORT_PATH = Path("reports/validation.md")
FIXTURES_REPORT_PATH = Path("reports/fixtures/validation.md")
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
WORST_DAYS = 20


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
    return frame.dropna(subset=[TARGET, *INPUTS, *MODEL_FEATURES])


def candidate_errors(
    frame: pd.DataFrame, ridge: Pipeline, hgb: Pipeline
) -> pd.DataFrame:
    rows = scored_rows(frame)
    predictions = baseline_predictions(rows)
    predictions["ridge"] = ridge_predictions(ridge, rows)
    predictions["hgb"] = hgb_predictions(hgb, rows)
    return predictions.sub(rows[TARGET], axis=0)


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


def validation_grid(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    candidates: Mapping[object, object],
    fit: Callable[[pd.DataFrame, object], Pipeline],
    predict: Callable[[Pipeline, pd.DataFrame], pd.Series],
    chosen: str,
) -> tuple[pd.DataFrame, Pipeline]:
    rows = scored_rows(validation)
    if rows.empty:
        raise ValueError(
            f"validation split has 0 scored rows out of {len(validation)}; "
            f"{chosen} cannot be chosen"
        )
    fits = {label: fit(train, value) for label, value in candidates.items()}
    errors = pd.DataFrame(
        {label: predict(model, rows) for label, model in fits.items()}
    ).sub(rows[TARGET], axis=0)
    grid = overall_scores(errors)
    return grid, fits[grid["MAE"].idxmin()]


def alpha_grid(
    train: pd.DataFrame, validation: pd.DataFrame
) -> tuple[pd.DataFrame, Pipeline]:
    alphas = {alpha: alpha for alpha in ALPHAS}
    return validation_grid(
        train, validation, alphas, fit_ridge, ridge_predictions, "alpha"
    )


def hgb_label(params: Mapping[str, float]) -> str:
    return (
        f"lr={params['learning_rate']:g} iter={params['max_iter']} "
        f"leaves={params['max_leaf_nodes']}"
    )


def hgb_grid(
    train: pd.DataFrame, validation: pd.DataFrame
) -> tuple[pd.DataFrame, Pipeline]:
    params = {hgb_label(values): values for values in HGB_GRID}
    return validation_grid(
        train, validation, params, fit_hgb, hgb_predictions, "parameters"
    )


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


def worst_days(errors: pd.DataFrame, price: pd.Series) -> pd.DataFrame:
    day = delivery_day(errors.index)
    table = errors.abs().groupby(day).mean().add_prefix("MAE ")
    table.insert(0, "mean actual price", price.groupby(day).mean())
    table.insert(0, "rows", errors.groupby(day).size())
    table = table.nlargest(WORST_DAYS, "MAE hgb")
    table.index = table.index.strftime("%Y-%m-%d")
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
            **{
                f"missing {column}": int(part[column].isna().sum())
                for column in PRICE_FEATURES
            },
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
    train = split_rows(frame, "train")
    validation = split_rows(frame, "validation")
    grid, ridge = alpha_grid(train, validation)
    alpha = ridge.named_steps["ridge"].alpha
    grid.index = [f"{value:g}" for value in grid.index]
    boosting, hgb = hgb_grid(train, validation)
    chosen = hgb_label(hgb.named_steps["hgb"].get_params())
    errors = candidate_errors(validation, ridge, hgb)
    rows = validation.loc[errors.index]
    worst = worst_days(errors, rows[TARGET])
    sections = [
        ("Overall", markdown_table(overall_scores(errors), "candidate")),
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
            f"Worst {len(worst)} days by hgb MAE",
            "Local delivery days ranked by hgb daily MAE, highest first; hgb has "
            "the lowest overall validation MAE. Mean actual price and MAE are "
            "over the scored rows of each day.\n\n" + markdown_table(worst, "date"),
        ),
        (
            "Ridge alpha grid",
            "Ridge is fitted on train for each alpha and scored on validation. "
            f"Chosen alpha: {alpha:g}, the lowest validation MAE. Because "
            "validation chose it, its validation MAE is slightly optimistic; the "
            "single test run is the unbiased number.\n\n"
            + markdown_table(grid, "alpha"),
        ),
        (
            f"Ridge coefficients, alpha {alpha:g}",
            "Lags and rolling statistics are standardised with train mean and "
            "standard deviation, so their coefficients are EUR/MWh per train "
            "standard deviation. Hour, weekday and month are one-hot and the "
            "holiday flags are 0/1, so their coefficients are EUR/MWh. Every "
            "level of each calendar column is encoded, so only differences "
            "within a column are meaningful.\n\n"
            + markdown_table(ridge_coefficients(ridge), "input"),
        ),
        (
            "Gradient boosting grid",
            "Gradient boosting is fitted on train for each parameter set and "
            f"scored on validation; the chosen set, {chosen}, has the lowest "
            "validation MAE. Because validation chose it, its validation MAE is "
            "slightly optimistic for the same reason as the ridge alpha.\n\n"
            + markdown_table(boosting, "parameters"),
        ),
        (
            "Rows excluded for missing target or price features",
            markdown_table(excluded_counts(frame), "split"),
        ),
    ]
    text = [
        "# Baselines, ridge and gradient boosting on validation (2025)",
        "",
        "EUR/MWh. All candidates are scored on the same rows. Lags are elapsed "
        "UTC hours; hour and month are local time. Ridge is fitted on train "
        "(2001-2024); its scaling and one-hot encoding are fitted inside the "
        "pipeline on train rows only. Gradient boosting is fitted on train with "
        "the calendar columns as categoricals and no scaling.",
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
    parser = argparse.ArgumentParser(
        description="Score the baselines, ridge and gradient boosting on validation."
    )
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
