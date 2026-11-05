import numpy as np
import pandas as pd
import pytest

from elvarsel import evaluate, features, final_run, models

# Ends 2026-04-05 23:00 local, so the test split holds 95 whole days, one of
# them the 23-hour spring transition day 2026-03-29.
END_UTC = "2026-04-05T21:00"
TEST_ROWS = 95 * 24 - 1


def hourly(start: str, end: str) -> pd.DataFrame:
    index = pd.date_range(start, end, freq="h", tz="UTC", name="time_utc")
    price = 50 * np.sin(np.arange(len(index)) / 7) + np.arange(len(index)) / 100
    return pd.DataFrame({"price_eur": price}, index=index)


def final_features() -> pd.DataFrame:
    return features.build_features(hourly("2024-10-01", END_UTC))


def split_chunks(report: str, name: str) -> list[str]:
    return [chunk for chunk in report.split("### ") if chunk.startswith(name)]


def test_only_ridge_is_fitted_once_on_train_with_frozen_alpha(monkeypatch):
    fitted = []

    def recording_fit(train, alpha):
        fitted.append((train.index, alpha))
        return models.fit_ridge(train, alpha)

    def no_hgb(*args):
        raise AssertionError("gradient boosting fitted")

    monkeypatch.setattr(final_run, "fit_ridge", recording_fit)
    monkeypatch.setattr(evaluate, "fit_hgb", no_hgb)
    monkeypatch.setattr(models, "fit_hgb", no_hgb)

    report = final_run.final_report(final_features())

    assert len(fitted) == 1
    index, alpha = fitted[0]
    assert alpha == 1000.0
    assert evaluate.in_split(index, *evaluate.SPLITS["train"]).all()
    assert "hgb" not in report


def test_test_rows_cannot_change_validation_tables():
    frame = final_features()
    in_test = evaluate.in_split(frame.index, *evaluate.SPLITS["test"])
    absurd = frame.copy()
    absurd.loc[in_test, ["price_eur", *models.PRICE_FEATURES]] = 1e9

    real = final_run.final_report(frame)
    changed = final_run.final_report(absurd)

    assert len(split_chunks(real, "Validation")) == 5
    assert split_chunks(real, "Validation") == split_chunks(changed, "Validation")
    assert split_chunks(real, "Test") != split_chunks(changed, "Test")


def test_test_split_is_scored_whole_across_spring_transition():
    frame = final_features()
    ridge = models.fit_ridge(evaluate.split_rows(frame, "train"), 1000.0)

    errors = final_run.split_errors(frame, "test", ridge)
    span = final_run.scored_span({"test": errors}).loc["test"]
    per_day = errors.groupby(evaluate.delivery_day(errors.index)).size()

    assert span.to_dict() == {
        "scored rows": TEST_ROWS,
        "first UTC": "2025-12-31T23:00",
        "last UTC": END_UTC,
        "first local": "2026-01-01 00:00",
        "last local": "2026-04-05 23:00",
    }
    assert per_day[pd.Timestamp("2026-03-29")] == 23
    assert (per_day.drop(pd.Timestamp("2026-03-29")) == 24).all()


def test_excluded_counts_include_test_only_when_allowed():
    frame = final_features()

    counts = evaluate.excluded_counts(frame, allow_test=True)

    assert counts.loc["test", "rows"] == TEST_ROWS
    assert counts.loc["test", "excluded"] == 0
    assert counts.loc["test", "scored"] == TEST_ROWS
    held_out = evaluate.excluded_counts(frame)
    assert set(held_out.loc["test"]) == {evaluate.HELD_OUT}


def test_empty_test_split_raises():
    frame = features.build_features(hourly("2024-10-01", "2025-12-31T22:00"))

    with pytest.raises(ValueError, match="test split has 0 scored rows out of 0"):
        final_run.final_report(frame)


def test_written_report_has_test_and_validation_for_every_table(tmp_path):
    path = tmp_path / "features.csv"
    final_features().to_csv(path, lineterminator="\n")

    report = final_run.write_final_report(path, tmp_path / "test.md")

    assert (tmp_path / "test.md").read_text(encoding="utf-8") == report
    assert evaluate.HELD_OUT not in report
    sections = report.split("\n## ")[1:]
    titles = [section.splitlines()[0] for section in sections]
    assert titles[:4] == [
        "Scored rows",
        "Rows excluded for missing target or price features",
        "Overall",
        "By local hour of day",
    ]
    for section in sections[2:]:
        assert section.count("### Test") == 1
        assert section.count("### Validation") == 1
    assert "| ridge |" in report
