import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from elvarsel.features import LAG_HOURS, TARGET, WINDOW_HOURS

PRICE_FEATURES = [
    *(f"lag_{hours}" for hours in LAG_HOURS),
    f"roll_mean_{WINDOW_HOURS}",
    f"roll_std_{WINDOW_HOURS}",
]
CALENDAR_FEATURES = ["hour", "day_of_week", "month"]
FLAG_FEATURES = ["is_holiday", "is_day_after_holiday"]
MODEL_FEATURES = [*PRICE_FEATURES, *CALENDAR_FEATURES, *FLAG_FEATURES]
ALPHAS = (0.01, 0.1, 1.0, 10.0, 100.0, 1000.0)
HGB_GRID = tuple(
    {"learning_rate": rate, "max_iter": iterations, "max_leaf_nodes": leaves}
    for rate in (0.05, 0.1)
    for iterations in (200, 500)
    for leaves in (15, 31)
)


def ridge_pipeline(alpha: float) -> Pipeline:
    columns = ColumnTransformer(
        [
            ("scaled", StandardScaler(), PRICE_FEATURES),
            (
                "one_hot",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CALENDAR_FEATURES,
            ),
            ("flags", "passthrough", FLAG_FEATURES),
        ],
        verbose_feature_names_out=False,
    )
    return Pipeline([("columns", columns), ("ridge", Ridge(alpha=alpha))])


def fit_ridge(train: pd.DataFrame, alpha: float) -> Pipeline:
    rows = train.dropna(subset=[TARGET, *MODEL_FEATURES])
    return ridge_pipeline(alpha).fit(rows[MODEL_FEATURES], rows[TARGET])


def ridge_predictions(pipeline: Pipeline, rows: pd.DataFrame) -> pd.Series:
    return pd.Series(pipeline.predict(rows[MODEL_FEATURES]), index=rows.index)


def ridge_coefficients(pipeline: Pipeline) -> pd.DataFrame:
    ridge = pipeline.named_steps["ridge"]
    names = ["intercept", *pipeline.named_steps["columns"].get_feature_names_out()]
    return pd.DataFrame({"coefficient": [ridge.intercept_, *ridge.coef_]}, index=names)


def hgb_pipeline(params: dict[str, float]) -> Pipeline:
    columns = ColumnTransformer(
        [
            ("prices", "passthrough", PRICE_FEATURES),
            ("calendar", "passthrough", CALENDAR_FEATURES),
            ("flags", "passthrough", FLAG_FEATURES),
        ],
        verbose_feature_names_out=False,
    )
    first = len(PRICE_FEATURES)
    hgb = HistGradientBoostingRegressor(
        **params,
        categorical_features=list(range(first, first + len(CALENDAR_FEATURES))),
        early_stopping=False,
        random_state=0,
    )
    return Pipeline([("columns", columns), ("hgb", hgb)])


def fit_hgb(train: pd.DataFrame, params: dict[str, float]) -> Pipeline:
    rows = train.dropna(subset=[TARGET, *MODEL_FEATURES])
    return hgb_pipeline(params).fit(rows[MODEL_FEATURES], rows[TARGET])


def hgb_predictions(pipeline: Pipeline, rows: pd.DataFrame) -> pd.Series:
    return pd.Series(pipeline.predict(rows[MODEL_FEATURES]), index=rows.index)
