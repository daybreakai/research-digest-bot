import numpy as np
import pandas as pd
from typing import Literal

SERIES_TYPES = ["intermittent", "heavy_tailed", "non_constant_variance", "high_selling"]
TYPE_PROPORTIONS = [0.30, 0.25, 0.25, 0.20]
# Monthly is 60 (5 yrs) not 36 — CV with h=12, n_windows=3 needs 48 minimum
N_PERIODS: dict[str, int] = {"W": 156, "MS": 60}


def generate_benchmark(
    n_series: int = 10_000,
    freq: Literal["W", "MS"] = "W",
    seed: int = 42,
) -> pd.DataFrame:
    """Generate M5-style synthetic retail benchmark in long format."""
    rng = np.random.default_rng(seed)
    n_periods = N_PERIODS[freq]
    start = "2020-01-06" if freq == "W" else "2020-01-01"
    dates = pd.date_range(start=start, periods=n_periods, freq=freq)

    type_counts = np.round(np.array(TYPE_PROPORTIONS) * n_series).astype(int)
    type_counts[-1] = n_series - type_counts[:-1].sum()
    series_types = np.repeat(SERIES_TYPES, type_counts)

    records = []
    for i, stype in enumerate(series_types):
        uid = f"{stype}_{i:05d}"
        y = _generate_series(stype, n_periods, rng)
        for d, v in zip(dates, y):
            records.append({"unique_id": uid, "ds": d, "y": float(v), "series_type": stype})

    return pd.DataFrame(records)


def _generate_series(stype: str, n: int, rng: np.random.Generator) -> np.ndarray:
    generators = {
        "intermittent": _intermittent,
        "heavy_tailed": _heavy_tailed,
        "non_constant_variance": _non_constant_variance,
        "high_selling": _high_selling,
    }
    return _add_m5_effects(generators[stype](n, rng), rng)


def _add_m5_effects(y: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Apply holiday spikes, level shifts, zero floor, integer rounding."""
    n = len(y)
    # Holiday/event spikes (~8/year, decay 1–2 periods after)
    n_spikes = max(1, int(round(n / 52 * 8)))
    spike_locs = rng.choice(n - 2, size=min(n_spikes, n - 2), replace=False)
    for loc in spike_locs:
        mult = rng.uniform(1.5, 4.0)
        y[loc] *= mult
        if loc + 1 < n:
            y[loc + 1] *= 1.0 + (mult - 1.0) * 0.4

    # 1–2 permanent level shifts in middle 50% of series
    lo, hi = n // 4, 3 * n // 4
    n_shifts = int(rng.integers(1, 3))
    if hi > lo + n_shifts:
        shift_locs = sorted(rng.choice(range(lo, hi), size=n_shifts, replace=False))
        for loc in shift_locs:
            direction = int(rng.choice([-1, 1]))
            y[loc:] *= 1.0 + direction * rng.uniform(0.3, 0.7)

    y = np.clip(y, 0, None)
    return np.round(y).astype(float)


def _intermittent(n: int, rng: np.random.Generator) -> np.ndarray:
    p = rng.uniform(0.2, 0.4)
    arrivals = rng.binomial(1, p, size=n).astype(float)
    magnitudes = rng.lognormal(mean=1.5, sigma=0.8, size=n)
    return arrivals * magnitudes


def _heavy_tailed(n: int, rng: np.random.Generator) -> np.ndarray:
    n_param = float(rng.uniform(1.5, 3.0))
    p_param = float(rng.uniform(0.1, 0.3))
    return rng.negative_binomial(n=n_param, p=p_param, size=n).astype(float)


def _non_constant_variance(n: int, rng: np.random.Generator) -> np.ndarray:
    trend = np.linspace(10.0, float(rng.uniform(8, 25)), n)
    seasonality = 1.0 + 0.3 * np.sin(2 * np.pi * np.arange(n) / 52)
    sigma = np.ones(n)
    eps = rng.standard_normal(n)
    for t in range(1, n):
        sigma[t] = float(np.sqrt(max(
            0.01,
            0.1 + 0.7 * (trend[t - 1] * 0.1 * eps[t - 1]) ** 2 + 0.2 * sigma[t - 1] ** 2,
        )))
    return trend * seasonality + sigma * eps


def _high_selling(n: int, rng: np.random.Generator) -> np.ndarray:
    base = float(rng.uniform(50.0, 300.0))
    trend = np.linspace(base, base * float(rng.uniform(0.9, 1.2)), n)
    return trend + rng.normal(0, base * 0.08, size=n)
