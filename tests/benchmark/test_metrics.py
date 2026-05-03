import numpy as np
import pytest
import pandas as pd
from research_digest.benchmark.metrics import (
    rmse, mae, me, wmape, metrics_by_series_type,
)


def test_rmse_perfect():
    y = np.array([1.0, 2.0, 3.0])
    assert rmse(y, y) == 0.0


def test_rmse_known():
    y_true = np.array([0.0, 0.0, 0.0])
    y_pred = np.array([3.0, 4.0, 0.0])
    assert abs(rmse(y_true, y_pred) - np.sqrt(25 / 3)) < 1e-9


def test_mae_perfect():
    y = np.array([1.0, 2.0, 3.0])
    assert mae(y, y) == 0.0


def test_mae_known():
    assert abs(mae(np.array([0.0, 0.0]), np.array([1.0, 3.0])) - 2.0) < 1e-9


def test_me_positive_bias():
    assert abs(me(np.array([1.0, 1.0]), np.array([3.0, 3.0])) - 2.0) < 1e-9


def test_me_negative_bias():
    assert abs(me(np.array([3.0, 3.0]), np.array([1.0, 1.0])) - (-2.0)) < 1e-9


def test_me_zero_bias():
    y = np.array([1.0, 2.0, 3.0])
    assert me(y, y) == 0.0


def test_wmape_perfect():
    y = np.array([1.0, 2.0, 3.0])
    assert wmape(y, y) == 0.0


def test_wmape_known():
    # |2-1|=1, |4-4|=0; sum(y_true)=6 → 1/6
    assert abs(wmape(np.array([2.0, 4.0]), np.array([1.0, 4.0])) - 1 / 6) < 1e-9


def test_wmape_zeros_in_y_true():
    # |0-1|+|0-1|+|4-4|=2; sum(|y_true|)=4 → 0.5
    assert abs(wmape(np.array([0.0, 0.0, 4.0]), np.array([1.0, 1.0, 4.0])) - 0.5) < 1e-9


def test_wmape_all_zeros_returns_nan():
    assert np.isnan(wmape(np.array([0.0, 0.0]), np.array([1.0, 1.0])))


def test_metrics_by_series_type_returns_correct_rows():
    cv_df = pd.DataFrame({
        "unique_id": ["a", "a", "b", "b"],
        "ds": pd.date_range("2020-01-01", periods=4, freq="W"),
        "y": [1.0, 2.0, 3.0, 4.0],
        "y_hat": [1.0, 2.0, 3.0, 4.0],
        "cutoff": ["c"] * 4,
        "series_type": ["intermittent", "intermittent", "high_selling", "high_selling"],
    })
    result = metrics_by_series_type(cv_df)
    assert set(result["series_type"]) == {"intermittent", "high_selling", "ALL"}
    assert set(result.columns) == {"series_type", "rmse", "mae", "me", "wmape"}


def test_metrics_by_series_type_perfect_predictions_are_zero():
    cv_df = pd.DataFrame({
        "unique_id": ["a", "b"],
        "ds": pd.date_range("2020-01-01", periods=2, freq="W"),
        "y": [2.0, 4.0],
        "y_hat": [2.0, 4.0],
        "cutoff": ["c", "c"],
        "series_type": ["intermittent", "intermittent"],
    })
    result = metrics_by_series_type(cv_df)
    assert (result["rmse"] == 0.0).all()
    assert (result["mae"] == 0.0).all()
    assert (result["me"] == 0.0).all()
    assert (result["wmape"] == 0.0).all()
