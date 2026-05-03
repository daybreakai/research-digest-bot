import pytest
import numpy as np
import pandas as pd
from research_digest.benchmark.data import (
    generate_benchmark,
    SERIES_TYPES,
    TYPE_PROPORTIONS,
    N_PERIODS,
)


def test_output_columns():
    df = generate_benchmark(n_series=50, freq="W", seed=0)
    assert set(df.columns) == {"unique_id", "ds", "y", "series_type"}


def test_weekly_series_count():
    df = generate_benchmark(n_series=100, freq="W", seed=0)
    assert df["unique_id"].nunique() == 100


def test_monthly_series_count():
    df = generate_benchmark(n_series=100, freq="MS", seed=0)
    assert df["unique_id"].nunique() == 100


def test_weekly_period_count():
    df = generate_benchmark(n_series=10, freq="W", seed=0)
    counts = df.groupby("unique_id")["ds"].count().unique()
    assert list(counts) == [N_PERIODS["W"]]


def test_monthly_period_count():
    df = generate_benchmark(n_series=10, freq="MS", seed=0)
    counts = df.groupby("unique_id")["ds"].count().unique()
    assert list(counts) == [N_PERIODS["MS"]]


def test_non_negative():
    df = generate_benchmark(n_series=100, freq="W", seed=0)
    assert (df["y"] >= 0).all()


def test_integer_values():
    df = generate_benchmark(n_series=100, freq="W", seed=0)
    assert (df["y"] % 1 == 0).all()


def test_series_type_set():
    df = generate_benchmark(n_series=200, freq="W", seed=0)
    assert set(df["series_type"].unique()) == set(SERIES_TYPES)


def test_series_type_proportions():
    df = generate_benchmark(n_series=1000, freq="W", seed=0)
    counts = df.drop_duplicates("unique_id")["series_type"].value_counts(normalize=True)
    for stype, expected in zip(SERIES_TYPES, TYPE_PROPORTIONS):
        actual = counts.get(stype, 0.0)
        assert abs(actual - expected) < 0.05, f"{stype}: expected ~{expected}, got {actual:.3f}"


def test_deterministic():
    df1 = generate_benchmark(n_series=50, freq="W", seed=42)
    df2 = generate_benchmark(n_series=50, freq="W", seed=42)
    pd.testing.assert_frame_equal(df1, df2)


def test_different_seeds_differ():
    df1 = generate_benchmark(n_series=50, freq="W", seed=42)
    df2 = generate_benchmark(n_series=50, freq="W", seed=99)
    assert not df1["y"].equals(df2["y"])


def test_monthly_cv_compatible():
    """60 monthly periods supports h=12, n_windows=3 (requires 48 minimum)."""
    assert N_PERIODS["MS"] >= 12 * (3 + 1)
