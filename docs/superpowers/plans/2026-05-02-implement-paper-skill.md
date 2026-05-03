# implement-paper Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `/implement-paper` slash command — the third agent in the research flywheel — which interviews the user, generates a constrained forecasting implementation, runs it against a synthetic M5-style benchmark with cross-validation, and writes results back to the Obsidian vault.

**Architecture:** Two-phase skill: Phase 1 loads Alfred's paper cache and vault context, conducts a structured interview, and commits a plan to the lab notebook. Phase 2 is triggered by a second invocation, reads the plan, generates Python code constrained to four allowed libraries, runs it against a shared synthetic benchmark via `.cross_validation()`, and produces a README and experiment verdict. Shared benchmark utilities live in `research_digest/benchmark/` and are copied as standalone files into each experiment directory at creation time.

**Tech Stack:** Python, numpy/pandas/scipy (data), scikit-learn/NeuralForecast/StatsForecast/MLForecast (implementations), pytest (tests), SKILL.md markdown (skill instructions for Claude Code)

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `research_digest/benchmark/__init__.py` | Package marker |
| Create | `research_digest/benchmark/data.py` | Synthetic M5-style benchmark data generator |
| Create | `research_digest/benchmark/metrics.py` | RMSE, MAE, ME, wMAPE; per-series-type aggregation |
| Create | `tests/benchmark/__init__.py` | Test package marker |
| Create | `tests/benchmark/test_data.py` | Tests for data generator |
| Create | `tests/benchmark/test_metrics.py` | Tests for metric functions |
| Create | `~/.claude/skills/implement-paper/templates/benchmark.py` | Runner template copied into each experiment dir |
| Modify | `~/.claude/skills/alfred/SKILL.md` | Add step 4h: write paper-cache.json |
| Create | `~/.claude/skills/implement-paper/SKILL.md` | Full Phase 1 + Phase 2 skill instructions |

> **Spec clarification on monthly series length:** The spec says 36 monthly periods but `h=12, n_windows=3` requires `h*(n_windows+1)=48` points minimum. Monthly is set to **60 periods (5 years)** throughout. `N_PERIODS = {"W": 156, "MS": 60}`.

---

## Task 1: Alfred step 4h — paper cache write

**Files:**
- Modify: `~/.claude/skills/alfred/SKILL.md`

- [ ] **Step 1: Open the file and locate step 4g**

```bash
grep -n "4g\|Mark as answered" ~/.claude/skills/alfred/SKILL.md
```
Expected: a line showing `**4g. Mark as answered**`

- [ ] **Step 2: Add step 4h immediately after step 4g**

Find the exact block:
```
**4g. Mark as answered**
Append the `@alfred` message's `ts` to `answered_ts`. Write updated `alfred-answered.json`.
```

Replace with:
```
**4g. Mark as answered**
Append the `@alfred` message's `ts` to `answered_ts`. Write updated `alfred-answered.json`.

**4h. Write to paper cache**

Append to `~/.claude/skills/alfred/paper-cache.json`:

```json
{
  "url": "<paper url from step 4a>",
  "title": "<paper title>",
  "summary": "<Alfred's answer text from step 4d, trimmed to ~200 words>",
  "methods_summary": "<1–2 sentences describing the core method of the paper>",
  "connections": ["<each → connection line Alfred generated in step 4d, if any>"]
}
```

If `paper-cache.json` does not exist, create it as an empty JSON array `[]` first. If the URL already exists in the cache, skip — do not overwrite (idempotent).
```

- [ ] **Step 3: Verify the file still has valid structure**

```bash
grep -c "^##\|^\*\*[0-9]" ~/.claude/skills/alfred/SKILL.md
```
Expected: count ≥ 10 (confirms headings and step markers are intact)

- [ ] **Step 4: Commit**

```bash
git -C ~/.claude add skills/alfred/SKILL.md
git -C ~/.claude commit -m "feat(alfred): add step 4h — write paper-cache.json after answering"
```

---

## Task 2: Benchmark data generator

**Files:**
- Create: `research_digest/benchmark/__init__.py`
- Create: `research_digest/benchmark/data.py`
- Create: `tests/benchmark/__init__.py`
- Create: `tests/benchmark/test_data.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/benchmark/__init__.py` (empty):
```python
```

Create `tests/benchmark/test_data.py`:
```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/jackrodenberg/research-digest-bot && python -m pytest tests/benchmark/test_data.py -v 2>&1 | head -20
```
Expected: `ModuleNotFoundError: No module named 'research_digest.benchmark'`

- [ ] **Step 3: Create the package and implement the generator**

Create `research_digest/benchmark/__init__.py` (empty):
```python
```

Create `research_digest/benchmark/data.py`:
```python
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
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd /Users/jackrodenberg/research-digest-bot && python -m pytest tests/benchmark/test_data.py -v
```
Expected: all 12 tests PASS

- [ ] **Step 5: Commit**

```bash
git add research_digest/benchmark/__init__.py research_digest/benchmark/data.py tests/benchmark/__init__.py tests/benchmark/test_data.py
git commit -m "feat(benchmark): add M5-style synthetic retail data generator"
```

---

## Task 3: Metrics module

**Files:**
- Create: `research_digest/benchmark/metrics.py`
- Create: `tests/benchmark/test_metrics.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/benchmark/test_metrics.py`:
```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/jackrodenberg/research-digest-bot && python -m pytest tests/benchmark/test_metrics.py -v 2>&1 | head -10
```
Expected: `ImportError: cannot import name 'rmse' from 'research_digest.benchmark.metrics'`

- [ ] **Step 3: Implement metrics.py**

Create `research_digest/benchmark/metrics.py`:
```python
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
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd /Users/jackrodenberg/research-digest-bot && python -m pytest tests/benchmark/test_metrics.py -v
```
Expected: all 13 tests PASS

- [ ] **Step 5: Run all benchmark tests together**

```bash
cd /Users/jackrodenberg/research-digest-bot && python -m pytest tests/benchmark/ -v
```
Expected: all 25 tests PASS

- [ ] **Step 6: Commit**

```bash
git add research_digest/benchmark/metrics.py tests/benchmark/test_metrics.py
git commit -m "feat(benchmark): add RMSE/MAE/ME/wMAPE metrics with per-series-type aggregation"
```

---

## Task 4: Benchmark runner template

**Files:**
- Create: `~/.claude/skills/implement-paper/templates/benchmark.py`

This file is copied verbatim into each experiment directory. `make_model()` and `make_control()` are filled in by the Phase 2 skill when generating the experiment.

- [ ] **Step 1: Create the template directory**

```bash
mkdir -p ~/.claude/skills/implement-paper/templates
```

- [ ] **Step 2: Write the template**

Create `~/.claude/skills/implement-paper/templates/benchmark.py`:
```python
"""
Benchmark runner — generated by /implement-paper.
Run: python benchmark.py
Requires: pip install statsforecast mlforecast neuralforecast scikit-learn
"""
import json
from pathlib import Path
import pandas as pd

from benchmark_data import generate_benchmark
from metrics import metrics_by_series_type

# ── Configured per experiment ─────────────────────────────────────────────────
HORIZONS = [4, 8]        # forecast horizons — one CV pass per element
N_WINDOWS = 3            # equally spaced CV folds (step_size=h)
FREQUENCIES = ["W", "MS"]
SEED = 42
# ─────────────────────────────────────────────────────────────────────────────


def make_model(freq: str, h: int):
    """Implementation model. Filled in by /implement-paper Phase 2."""
    raise NotImplementedError


def make_control(freq: str, h: int):
    """Control baseline model. Filled in by /implement-paper Phase 2."""
    raise NotImplementedError


def _run_cv(
    model_fn,
    df_train: pd.DataFrame,
    h: int,
    freq: str,
    meta: pd.DataFrame,
) -> pd.DataFrame:
    model = model_fn(freq=freq, h=h)
    lib = type(model).__module__.split(".")[0]

    if lib == "neuralforecast":
        # h is set at model init for NeuralForecast, not in cross_validation
        cv = model.cross_validation(df_train, step_size=h, n_windows=N_WINDOWS)
    elif lib in ("statsforecast", "mlforecast"):
        cv = model.cross_validation(df_train, h=h, step_size=h, n_windows=N_WINDOWS)
    else:
        raise ValueError(
            f"Unsupported library: {lib!r}. "
            "Allowed: neuralforecast, statsforecast, mlforecast."
        )

    pred_col = next(
        c for c in cv.columns if c not in ("unique_id", "ds", "cutoff", "y")
    )
    cv = cv.rename(columns={pred_col: "y_hat"})
    return cv.merge(meta, on="unique_id")


def main() -> None:
    all_results: dict = {}

    for freq in FREQUENCIES:
        df = generate_benchmark(n_series=10_000, freq=freq, seed=SEED)
        df_train = df[["unique_id", "ds", "y"]]
        meta = df[["unique_id", "series_type"]].drop_duplicates()

        for h in HORIZONS:
            key = f"{freq}_h{h}"
            impl_cv = _run_cv(make_model, df_train, h=h, freq=freq, meta=meta)
            ctrl_cv = _run_cv(make_control, df_train, h=h, freq=freq, meta=meta)

            impl_m = (
                metrics_by_series_type(impl_cv)
                .add_prefix("impl_")
                .rename(columns={"impl_series_type": "series_type"})
            )
            ctrl_m = (
                metrics_by_series_type(ctrl_cv)
                .add_prefix("ctrl_")
                .rename(columns={"ctrl_series_type": "series_type"})
            )
            merged = impl_m.merge(ctrl_m, on="series_type")
            for metric in ("rmse", "mae", "me", "wmape"):
                merged[f"delta_{metric}"] = merged[f"impl_{metric}"] - merged[f"ctrl_{metric}"]

            all_results[key] = merged.to_dict(orient="records")
            _print_block(key, merged)

    Path("results.json").write_text(json.dumps(all_results, indent=2))
    print("\nResults written to results.json")


def _print_block(key: str, df: pd.DataFrame) -> None:
    print(f"\n=== {key} ===")
    print(f"{'Series Type':<28}  {'ctrl wMAPE':>10}  {'impl wMAPE':>10}  {'Δ':>+8}  {'ctrl MAE':>9}  {'impl MAE':>9}  {'Δ':>+7}  {'ME Δ':>+7}")
    for _, row in df.iterrows():
        print(
            f"{row['series_type']:<28}"
            f"  {row['ctrl_wmape']:>10.4f}  {row['impl_wmape']:>10.4f}  {row['delta_wmape']:>+8.4f}"
            f"  {row['ctrl_mae']:>9.2f}  {row['impl_mae']:>9.2f}  {row['delta_mae']:>+7.2f}"
            f"  {row['delta_me']:>+7.2f}"
        )


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Verify the template is importable (syntax check)**

```bash
python -c "import ast; ast.parse(open('~/.claude/skills/implement-paper/templates/benchmark.py'.replace('~', __import__('os').path.expanduser('~'))).read()); print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git -C ~/.claude add skills/implement-paper/templates/benchmark.py
git -C ~/.claude commit -m "feat(implement-paper): add benchmark runner template"
```

---

## Task 5: implement-paper SKILL.md

**Files:**
- Create: `~/.claude/skills/implement-paper/SKILL.md`

This is the skill instruction file Claude Code follows when `/implement-paper` is invoked. It must be complete — no placeholders, all edge cases handled.

- [ ] **Step 1: Create the skill file**

Create `~/.claude/skills/implement-paper/SKILL.md`:

````markdown
---
name: implement-paper
description: Two-phase forecasting experiment builder. Phase 1 interviews the user and writes an experiment plan to the Obsidian vault. Phase 2 (second invocation with same URL) generates a constrained implementation, runs cross-validation against a synthetic M5-style benchmark, writes a README, and updates the vault experiment entry. Allowed frameworks: Sklearn, NeuralForecast, StatsForecast, MLForecast.
---

# implement-paper

## Trigger

`/implement-paper <arxiv-url>`

Invoked twice for one experiment:
1. First invocation → Phase 1 (interview + plan)
2. Second invocation with same URL → Phase 2 (implement + benchmark)

---

## Phase Detection

Before doing anything, grep the lab notebook to check if this URL has already been planned:

```bash
grep -rl "<URL>" ~/ObsidianVault/DaybreakResearch/03-LabNotebook/ 2>/dev/null
```

- **No match** → Phase 1
- **Match found, `verdict: null` in frontmatter** → Phase 2
- **Match found, `verdict:` is set (confirmed/partial/refuted)** → Tell the user: "This experiment already has a verdict. Invoke `/implement-paper <url>` to start a new variant, or open the experiment file to review results." Then stop.

---

## Allowed Frameworks

Implementations may ONLY import from:
- `sklearn` (scikit-learn) — feature engineering, pipelines, baselines
- `neuralforecast` — DL-based time series models
- `statsforecast` — statistical and classical TS models
- `mlforecast` — ML-based recursive/direct forecasting

Plus data primitives: `numpy`, `pandas`, `scipy`.

**If the paper requires something outside these four:** present two constraint-compliant alternatives during the interview (step 3). Never silently import a disallowed library. Never ask for authorization mid-implementation.

---

## Phase 1 — Interview & Plan

### Context Loading (parallel)

Before asking the first question, read all three sources simultaneously:

1. `~/.claude/skills/alfred/paper-cache.json` — find the entry where `"url"` matches the provided URL (exact match or arxiv ID match, e.g. `2404.12345` matches `https://arxiv.org/abs/2404.12345`)
2. `~/ObsidianVault/DaybreakResearch/05-ClaudeContext/active-briefing.md`
3. All `.md` files in `~/ObsidianVault/DaybreakResearch/03-LabNotebook/` — extract `hypothesis:` and `verdict:` frontmatter from each; keep only those where `verdict: null` or `verdict` is absent

**If the URL is not in Alfred's cache:** stop and say:
> "This paper hasn't been processed by Alfred yet. Ask `@alfred` about it in a `#research-digest` thread first, then invoke `/implement-paper` again."

### Interview Sequence

Ask one question at a time. Use the loaded context to make questions specific — never generic.

---

**Question 1 — Scope**

State Alfred's `methods_summary` for the paper, then ask:
> "Alfred summarized the method as: [methods_summary]. Which part do you want to implement — the full method, a specific component (e.g. the loss function, the encoder), or an adaptation of it?"

---

**Question 2 — Existing experiment (only if Alfred flagged connections)**

If Alfred's `connections` list is non-empty and any open hypothesis in the lab notebook is related:
> "Alfred noted this paper connects to: [connection text]. Should this implementation extend that experiment, or stand alone as a new one?"

Skip this question if no connections or no matching open hypothesis.

---

**Question 3 — Framework mapping**

Based on the scope answer, propose a specific mapping to the allowed stack:
> "The paper's [mechanism from scope answer] maps to [specific class/approach in MLForecast/NeuralForecast/StatsForecast/Sklearn]. Here's the plan: [one paragraph describing exactly what code you'd write — which class, which parameters, what the custom piece looks like]. Does this match your intent, or should we adjust?"

If the mechanism cannot be expressed in the allowed stack, say:
> "This approach requires [library X] which is outside the allowed stack. Two compliant alternatives: (A) [alternative using allowed lib]; (B) [alternative using allowed lib]. Which would you like to pursue?"

---

**Question 4 — Control / Baseline**

Infer the control from the scope:
- Modifying a loss function → vanilla version of the same model with default loss
- Modifying a model architecture → base architecture without the modification
- Novel method applied to a standard problem → strongest StatsForecast or MLForecast baseline applicable

If unambiguous, confirm:
> "I'll use [vanilla X with config Y] as the control baseline. Does that work?"

**If at all unclear**, do not guess — enter a sub-interview:
> "I'm not confident what the right baseline is. Tell me in natural language what you want to benchmark against."

Continue asking until you can state the control as: model name, library, key hyperparameters. Show the user the exact control spec and ask for explicit approval before proceeding. **Do not write the plan until the control is approved.**

---

**Question 5 — Benchmark config**

> "Run weekly only, monthly only, or both? What horizons should I benchmark? (e.g. `[4, 8, 13]` for weekly or `[3, 6, 12]` for monthly — I'll run a separate cross-validation pass for each horizon.) Standard metrics are RMSE, MAE, ME (bias), and wMAPE. Default is 3 CV folds per horizon. Any changes?"

---

**Question 6 — Success criterion**

> "What result would mark this experiment as `verdict: confirmed`? Be specific — e.g. '>5% wMAPE improvement over control on intermittent series at h=8' or 'lower ME (bias closer to zero) on heavy-tailed series at all horizons'."

---

### Writing the Plan

After all questions are approved, derive the experiment slug:
- Format: `YYYY-MM-DD-<first-5-words-of-paper-title-in-kebab-case>`
- Example: `2026-05-02-zeroinflated-loss-for-nhits`
- Today's date is available from context; use it

Write the experiment file to `~/ObsidianVault/DaybreakResearch/03-LabNotebook/<slug>.md`:

```markdown
---
hypothesis: "<scope answer distilled to one sentence>"
verdict: null
papers: "[<paper title>](<url>)"
---

## Implementation Plan

**Framework:** <chosen lib(s)>
**Control:** <exact control spec: model name, library, key hyperparameters>
**Benchmark:** <weekly / monthly / both>, 10k series each
**Horizons:** [<list from question 5>]
**CV folds:** <n_windows from question 5, default 3>
**Success criterion:** <from question 6>

### Method Mapping
<The one-paragraph framework mapping description agreed in question 3>

### Scope
<What is being implemented and what is explicitly out of scope>

## Links
- Papers: [<paper title>](<url>)
- Code: ~/DaybreakResearch/implementations/<slug>/
```

After writing, tell the user:
> "Plan written to `~/ObsidianVault/DaybreakResearch/03-LabNotebook/<slug>.md`. Review it, then invoke `/implement-paper <url>` again to start the implementation."

---

## Phase 2 — Implementation

### Setup

1. Find the experiment file (same grep as phase detection)
2. Read its full contents — extract: Framework, Control, Horizons list, CV folds, Success criterion, Method Mapping paragraph, Scope section, paper title + url from Papers: link
3. Derive the slug from the filename
4. Create the experiment directory:

```bash
mkdir -p ~/DaybreakResearch/implementations/<slug>
```

5. Copy the shared modules into the experiment directory:

```bash
cp ~/research-digest-bot/research_digest/benchmark/data.py ~/DaybreakResearch/implementations/<slug>/benchmark_data.py
cp ~/research-digest-bot/research_digest/benchmark/metrics.py ~/DaybreakResearch/implementations/<slug>/metrics.py
cp ~/.claude/skills/implement-paper/templates/benchmark.py ~/DaybreakResearch/implementations/<slug>/benchmark.py
```

### Generating model.py

Write `~/DaybreakResearch/implementations/<slug>/model.py` containing the implementation. Rules:

- Only import from: `numpy`, `pandas`, `scipy`, `sklearn`, `neuralforecast`, `statsforecast`, `mlforecast`
- Export two callables: `make_model(freq: str, h: int)` and `make_control(freq: str, h: int)` — both return a fitted-ready model instance
- For NeuralForecast models: `h` is passed to the model constructor, e.g. `NHITS(h=h, ...)`; wrap in `NeuralForecast([model], freq=freq)`
- For StatsForecast models: return `StatsForecast([Model(...)], freq=freq)`
- For MLForecast models: return a configured `MLForecast(models=[...], freq=freq, ...)`

Example structure for a NeuralForecast implementation:
```python
from neuralforecast import NeuralForecast
from neuralforecast.models import NHITS

def make_model(freq: str, h: int):
    return NeuralForecast(
        models=[NHITS(h=h, input_size=2*h, <paper-specific params>)],
        freq=freq,
    )

def make_control(freq: str, h: int):
    return NeuralForecast(
        models=[NHITS(h=h, input_size=2*h)],  # vanilla defaults
        freq=freq,
    )
```

### Configuring benchmark.py

Edit the `~/DaybreakResearch/implementations/<slug>/benchmark.py` copy (do not edit the template):

1. Set `HORIZONS`, `N_WINDOWS`, `FREQUENCIES` from the plan
2. Replace the `make_model` and `make_control` stub bodies with:
   ```python
   from model import make_model, make_control
   ```
   Then delete the `raise NotImplementedError` bodies and replace with the above import at the top of the file (remove the stub definitions entirely)

### Running the Benchmark

```bash
cd ~/DaybreakResearch/implementations/<slug> && python benchmark.py
```

If the run fails:
- `ModuleNotFoundError`: a required library isn't installed — install it (`pip install <lib>`) and retry
- `NotImplementedError`: `make_model` or `make_control` stubs weren't replaced — fix benchmark.py
- Any other error: read the traceback, fix the root cause in model.py or benchmark.py, retry

Do not proceed to README generation until `results.json` exists and is non-empty.

### Writing README.md

Read `results.json`. Write `~/DaybreakResearch/implementations/<slug>/README.md`:

```markdown
# <paper title>

<summary from Alfred's paper-cache.json entry>

**Paper:** <url>
**Implemented:** <today's date YYYY-MM-DD>
**Frameworks:** <list of libs used>

## Method

<Method Mapping paragraph from plan, followed by Scope section>

## Control Baseline

<Exact control spec from plan>

## Results

<One block per freq × horizon, e.g.:>

### Weekly · h=4 (3 folds, avg)
| Series Type | ctrl RMSE | impl RMSE | Δ | ctrl MAE | impl MAE | Δ | ctrl ME | impl ME | Δ | ctrl wMAPE | impl wMAPE | Δ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| intermittent | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |
| heavy_tailed | ... |
| non_constant_variance | ... |
| high_selling | ... |
| ALL | ... |

<repeat for each horizon × frequency>

**Series mix:** 30% intermittent · 25% heavy-tailed · 25% non-constant variance · 20% high-selling
**CV:** equally spaced folds, step_size=h, metrics averaged across folds

## Verdict

<one sentence: success_criterion from plan — met / partially met / not met, with the key number>
```

Fill every table cell from `results.json`. No placeholders. Round floats to 4 decimal places.

### Updating the Experiment File

Edit `~/ObsidianVault/DaybreakResearch/03-LabNotebook/<slug>.md`:

1. Set `verdict:` in frontmatter based on success criterion:
   - `confirmed` — criterion fully met
   - `partial` — improvement present but below threshold, or mixed across series types
   - `refuted` — no improvement or regression

2. Append after the `## Links` section:

```markdown
## Results

<verdict sentence>

| freq · h | Series Type | ctrl wMAPE | impl wMAPE | Δ wMAPE | ctrl MAE | impl MAE | Δ MAE | ME Δ |
|---|---|---|---|---|---|---|---|---|
<fill from results.json, ALL rows only>
```

---

## Edge Cases

| Situation | Action |
|---|---|
| URL not in Alfred cache | Halt — tell user to ask Alfred first |
| Lab notebook entry exists with a verdict | Halt — tell user experiment is complete, offer new variant |
| Paper requires out-of-stack library | Surface in interview with 2 compliant alternatives |
| Control is ambiguous | Sub-interview until explicit approval — never guess |
| benchmark.py run fails | Fix root cause, retry — do not skip or fake results |
| results.json missing after run | Do not write README — re-run benchmark |
````

- [ ] **Step 2: Verify the skill file has all required sections**

```bash
grep -c "Phase Detection\|Phase 1\|Phase 2\|Interview Sequence\|Allowed Frameworks\|Edge Cases" ~/.claude/skills/implement-paper/SKILL.md
```
Expected: `6`

- [ ] **Step 3: Verify all 6 interview questions are present**

```bash
grep -c "Question [1-6]" ~/.claude/skills/implement-paper/SKILL.md
```
Expected: `6`

- [ ] **Step 4: Commit**

```bash
git -C ~/.claude add skills/implement-paper/SKILL.md
git -C ~/.claude commit -m "feat(implement-paper): add Phase 1 + Phase 2 skill instructions"
```

---

## Task 6: Full test suite pass + repo commit

- [ ] **Step 1: Run the full existing test suite to confirm no regressions**

```bash
cd /Users/jackrodenberg/research-digest-bot && python -m pytest tests/ -v
```
Expected: all tests PASS (including pre-existing `test_server.py`, `test_session.py`, `test_state.py`, `test_tools.py`, plus the new benchmark tests)

- [ ] **Step 2: Commit all remaining benchmark files**

```bash
git add research_digest/benchmark/ tests/benchmark/
git commit -m "feat(benchmark): wire benchmark package into repo test suite"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] Alfred step 4h — Task 1
- [x] `paper-cache.json` schema — Task 1 (alfred SKILL.md) + Task 5 (skill reads it)
- [x] Phase detection by lab notebook grep — Task 5 SKILL.md
- [x] Experiment slug derivation — Task 5 SKILL.md
- [x] All 6 interview questions including control sub-interview — Task 5 SKILL.md
- [x] Plan file frontmatter format — Task 5 SKILL.md
- [x] `benchmark_data.py` with M5 realism layers — Task 2
- [x] 10k series, W=156 periods, MS=60 periods — Task 2
- [x] 4 series archetypes at correct proportions — Task 2
- [x] RMSE, MAE, ME, wMAPE — Task 3
- [x] `metrics_by_series_type` including ALL row — Task 3
- [x] `.cross_validation()` with `step_size=h` equally spaced folds — Task 4 template
- [x] NeuralForecast API difference (h at model init) — Task 4 template + Task 5 SKILL.md
- [x] Horizons list → one CV pass per element — Task 4 template
- [x] Control + implementation both run, delta computed — Task 4 template
- [x] README with per-horizon × frequency tables — Task 5 SKILL.md
- [x] Experiment file verdict update — Task 5 SKILL.md
- [x] Framework constraint enforcement with 2-alternative fallback — Task 5 SKILL.md
- [x] Phase 2 never starts before Phase 1 checkpoint — Task 5 SKILL.md (phase detection)
- [x] Standalone experiment dir (benchmark_data.py copied, not imported from package) — Task 5 SKILL.md
