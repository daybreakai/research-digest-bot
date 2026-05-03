import numpy as np
import pandas as pd


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_pred - y_true) ** 2)))


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_pred - y_true)))


def me(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Mean error (bias). Positive = over-forecast."""
    return float(np.mean(y_pred - y_true))


def wmape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Weighted MAPE. Returns nan when sum(|y_true|) == 0."""
    denom = float(np.sum(np.abs(y_true)))
    if denom == 0.0:
        return float("nan")
    return float(np.sum(np.abs(y_pred - y_true)) / denom)


def metrics_by_series_type(cv_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate CV results by series_type.
    cv_df must have columns: unique_id, ds, y, y_hat, cutoff, series_type
    Returns DataFrame with columns: series_type, rmse, mae, me, wmape
    Includes an ALL aggregate row.
    """
    rows = []
    for stype, grp in cv_df.groupby("series_type"):
        yt = grp["y"].to_numpy()
        yp = grp["y_hat"].to_numpy()
        rows.append({
            "series_type": stype,
            "rmse": rmse(yt, yp),
            "mae": mae(yt, yp),
            "me": me(yt, yp),
            "wmape": wmape(yt, yp),
        })
    yt = cv_df["y"].to_numpy()
    yp = cv_df["y_hat"].to_numpy()
    rows.append({
        "series_type": "ALL",
        "rmse": rmse(yt, yp),
        "mae": mae(yt, yp),
        "me": me(yt, yp),
        "wmape": wmape(yt, yp),
    })
    return pd.DataFrame(rows)[["series_type", "rmse", "mae", "me", "wmape"]]
