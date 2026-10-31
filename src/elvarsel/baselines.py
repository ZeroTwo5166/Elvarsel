import pandas as pd

INPUTS = ["lag_24", "lag_168"]


def baseline_predictions(features: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "persistence_24": features["lag_24"],
            "persistence_168": features["lag_168"],
            "mean_24_168": (features["lag_24"] + features["lag_168"]) / 2,
        }
    )
