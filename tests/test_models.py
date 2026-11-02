import numpy as np
import pandas as pd

from elvarsel import features, models


def hourly(start: str, end: str) -> pd.DataFrame:
    index = pd.date_range(start, end, freq="h", tz="UTC", name="time_utc")
    price = 50 * np.sin(np.arange(len(index)) / 7) + np.arange(len(index)) / 100
    return pd.DataFrame({"price_eur": price}, index=index)


def train_and_later(split: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = features.build_features(hourly("2024-01-01", "2024-07-01"))
    return df[df.index < split], df[df.index >= split]


def test_scaling_uses_train_mean_and_std():
    train, _ = train_and_later("2024-04-01")

    pipeline = models.fit_ridge(train, 1.0)

    rows = train.dropna(subset=[features.TARGET, *models.MODEL_FEATURES])
    scaler = pipeline.named_steps["columns"].named_transformers_["scaled"]
    assert np.allclose(scaler.mean_, rows[models.PRICE_FEATURES].mean())
    assert np.allclose(scaler.scale_, rows[models.PRICE_FEATURES].std(ddof=0))


def test_one_hot_categories_come_from_train_and_unseen_values_are_ignored():
    train, later = train_and_later("2024-02-29T23:00")

    pipeline = models.fit_ridge(train, 1.0)

    encoder = pipeline.named_steps["columns"].named_transformers_["one_hot"]
    months = encoder.categories_[models.CALENDAR_FEATURES.index("month")]
    assert months.tolist() == [1, 2]
    predictions = models.ridge_predictions(pipeline, later.dropna())
    assert predictions.notna().all()
    assert set(later.dropna()["month"]) - {1, 2}


def test_fit_drops_rows_with_missing_target_or_features():
    train, _ = train_and_later("2024-04-01")
    train.loc["2024-03-10T05:00", "price_eur"] = float("nan")
    rows = train.dropna(subset=[features.TARGET, *models.MODEL_FEATURES])

    fitted = models.ridge_coefficients(models.fit_ridge(train, 1.0))
    expected = models.ridge_coefficients(models.fit_ridge(rows, 1.0))

    assert len(rows) < len(train) - 336
    pd.testing.assert_frame_equal(fitted, expected)


def test_ridge_recovers_a_linear_target_at_small_alpha():
    rng = np.random.default_rng(0)
    df = features.build_features(hourly("2024-01-01", "2024-07-01"))
    df[models.PRICE_FEATURES] = rng.normal(
        50, 20, (len(df), len(models.PRICE_FEATURES))
    )
    df = df.assign(
        price_eur=5 + 3 * df["lag_24"] - 2 * df["lag_168"] + 4 * df["is_holiday"]
    )

    pipeline = models.fit_ridge(df, 0.01)

    assert np.allclose(
        models.ridge_predictions(pipeline, df), df["price_eur"], atol=1e-3
    )
    coefficients = models.ridge_coefficients(pipeline)["coefficient"]
    scale = pipeline.named_steps["columns"].named_transformers_["scaled"].scale_
    lag_24 = models.PRICE_FEATURES.index("lag_24")
    assert np.isclose(coefficients["lag_24"] / scale[lag_24], 3, atol=1e-3)
    assert np.isclose(coefficients["is_holiday"], 4, atol=1e-2)


def test_hgb_grid_is_the_eight_combinations():
    combinations = {tuple(params.items()) for params in models.HGB_GRID}

    assert len(models.HGB_GRID) == len(combinations) == 8
    assert {params["learning_rate"] for params in models.HGB_GRID} == {0.05, 0.1}
    assert {params["max_iter"] for params in models.HGB_GRID} == {200, 500}
    assert {params["max_leaf_nodes"] for params in models.HGB_GRID} == {15, 31}


def test_hgb_treats_calendar_columns_as_categorical_and_prices_raw():
    train, _ = train_and_later("2024-04-01")

    pipeline = models.fit_hgb(train, models.HGB_GRID[0])

    names = pipeline.named_steps["columns"].get_feature_names_out().tolist()
    categorical = pipeline.named_steps["hgb"].is_categorical_
    assert names == models.MODEL_FEATURES
    flagged = [name for name, flag in zip(names, categorical, strict=True) if flag]
    assert flagged == models.CALENDAR_FEATURES
    rows = train.dropna(subset=[features.TARGET, *models.MODEL_FEATURES])
    transformed = pipeline.named_steps["columns"].transform(rows[models.MODEL_FEATURES])
    assert np.array_equal(transformed, rows[models.MODEL_FEATURES].to_numpy())


def test_hgb_fit_drops_rows_with_missing_target_or_features():
    train, later = train_and_later("2024-04-01")
    train.loc["2024-03-10T05:00", "price_eur"] = float("nan")
    rows = train.dropna(subset=[features.TARGET, *models.MODEL_FEATURES])
    params = models.HGB_GRID[0]

    fitted = models.hgb_predictions(models.fit_hgb(train, params), later.dropna())
    expected = models.hgb_predictions(models.fit_hgb(rows, params), later.dropna())

    pd.testing.assert_series_equal(fitted, expected)


def test_hgb_predictions_are_deterministic():
    train, later = train_and_later("2024-04-01")
    params = models.HGB_GRID[-1]

    first = models.hgb_predictions(models.fit_hgb(train, params), later.dropna())
    second = models.hgb_predictions(models.fit_hgb(train, params), later.dropna())

    pd.testing.assert_series_equal(first, second, check_exact=True)
