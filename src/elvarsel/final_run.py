import argparse
from collections.abc import Callable, Mapping
from pathlib import Path

import pandas as pd
from sklearn.pipeline import Pipeline

from elvarsel.clean import LOCAL_TZ
from elvarsel.evaluate import (
    HIGH_PRICE_EUR,
    WORST_DAYS,
    baseline_and_ridge_errors,
    excluded_counts,
    extreme_scores,
    markdown_table,
    overall_scores,
    scored_rows,
    scores_by,
    split_rows,
    worst_days,
)
from elvarsel.features import FEATURES_PATH, TARGET
from elvarsel.models import fit_ridge

REPORT_PATH = Path("reports/test.md")
# Chosen on validation and frozen in docs/decisions.md, 2026-11-03.
RIDGE_ALPHA = 1000.0
SCORED_SPLITS = ("test", "validation")


def split_errors(frame: pd.DataFrame, name: str, ridge: Pipeline) -> pd.DataFrame:
    part = split_rows(frame, name, allow_test=True)
    if scored_rows(part).empty:
        raise ValueError(f"{name} split has 0 scored rows out of {len(part)}")
    return baseline_and_ridge_errors(part, ridge)


def scored_span(errors: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    spans = {}
    for name, split in errors.items():
        first, last = split.index.min(), split.index.max()
        spans[name] = {
            "scored rows": len(split),
            "first UTC": first.strftime("%Y-%m-%dT%H:%M"),
            "last UTC": last.strftime("%Y-%m-%dT%H:%M"),
            "first local": first.tz_convert(LOCAL_TZ).strftime("%Y-%m-%d %H:%M"),
            "last local": last.tz_convert(LOCAL_TZ).strftime("%Y-%m-%d %H:%M"),
        }
    return pd.DataFrame.from_dict(spans, orient="index", dtype="object")


def split_tables(
    errors: Mapping[str, pd.DataFrame],
    rows: Mapping[str, pd.DataFrame],
    table: Callable[[pd.DataFrame, pd.DataFrame], pd.DataFrame],
    index_name: str,
) -> str:
    parts = [
        f"### {name.capitalize()}\n\n"
        + markdown_table(table(errors[name], rows[name]), index_name)
        for name in SCORED_SPLITS
    ]
    return "\n\n".join(parts)


def final_report(frame: pd.DataFrame) -> str:
    ridge = fit_ridge(split_rows(frame, "train"), RIDGE_ALPHA)
    errors = {name: split_errors(frame, name, ridge) for name in SCORED_SPLITS}
    rows = {name: frame.loc[split.index] for name, split in errors.items()}
    sections = [
        ("Scored rows", markdown_table(scored_span(errors), "split")),
        (
            "Rows excluded for missing target or price features",
            markdown_table(excluded_counts(frame, allow_test=True), "split"),
        ),
        (
            "Overall",
            split_tables(errors, rows, lambda e, r: overall_scores(e), "candidate"),
        ),
        (
            "By local hour of day",
            split_tables(errors, rows, lambda e, r: scores_by(e, r["hour"]), "hour"),
        ),
        (
            "By local month",
            split_tables(errors, rows, lambda e, r: scores_by(e, r["month"]), "month"),
        ),
        (
            f"Extreme prices, high threshold {HIGH_PRICE_EUR} EUR/MWh (train p95)",
            split_tables(
                errors, rows, lambda e, r: extreme_scores(e, r[TARGET]), "band"
            ),
        ),
        (
            f"Worst {WORST_DAYS} days by ridge MAE",
            "Local delivery days ranked by ridge daily MAE, highest first. Mean "
            "actual price and MAE are over the scored rows of each day.\n\n"
            + split_tables(errors, rows, lambda e, r: worst_days(e, r[TARGET]), "date"),
        ),
    ]
    text = [
        "# Baselines and ridge on test (2026-01 to 2026-09), validation alongside",
        "",
        f"EUR/MWh. Ridge with alpha {RIDGE_ALPHA:g}, chosen on validation (see "
        "docs/decisions.md), is fitted once on train (2001-2024); its scaling and "
        "one-hot encoding are fitted inside the pipeline on train rows only. The "
        "same fitted model scores validation and test, so the validation tables "
        "match reports/validation.md. Gradient boosting is not run on test. "
        "Within each split all candidates are scored on the same rows: a row is "
        "excluded if its target or any price feature is missing. Lags are "
        "elapsed UTC hours; hour and month are local time.",
    ]
    for title, table in sections:
        text += ["", f"## {title}", "", table]
    return "\n".join(text) + "\n"


def write_final_report(features_path: Path, path: Path) -> str:
    frame = pd.read_csv(features_path, index_col="time_utc", parse_dates=["time_utc"])
    report = final_report(frame)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8", newline="\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Score the baselines and ridge once on the held-out test period."
    )
    parser.parse_args()
    write_final_report(FEATURES_PATH, REPORT_PATH)
    print(f"{REPORT_PATH} written from {FEATURES_PATH}")


if __name__ == "__main__":
    main()
