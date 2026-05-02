# implement-paper Skill — Design Spec
_2026-05-02_

## Overview

`/implement-paper <url>` is a two-phase slash command that turns a paper Alfred has already processed into a reproducible forecasting experiment. It is the third agent in the research flywheel: research-brief discovers → Alfred explains → implement-paper engineers.

The skill never fetches or re-analyzes the paper itself. Alfred is the knowledge layer. The implement skill is a pure engineering agent that reads Alfred's cached work, interviews the user, and produces a bulletproof implementation constrained to four allowed frameworks.

---

## Allowed Frameworks

Implementations may only import from:
- **Sklearn** (scikit-learn) — feature engineering, pipelines, baselines
- **NeuralForecast** — DL-based time series models
- **StatsForecast** — statistical and classical TS models
- **MLForecast** — ML-based recursive/direct forecasting

Plus data primitives: `numpy`, `pandas`, `scipy`.

If a paper's method requires something outside these four, the skill surfaces this **during the interview** with two constraint-compliant alternatives. It never silently breaks the rule and never asks for authorization mid-implementation.

---

## Flywheel Integration

```
research-brief
  └── discovers papers, links to open experiments in vault

alfred (existing + small addition)
  ├── answers paper questions in Slack
  └── [new] writes ~/.claude/skills/alfred/paper-cache.json
            { url, title, summary, methods_summary, connections[] }

/implement-paper <url>
  Phase 1 — Interview & Plan
    ├── read alfred/paper-cache.json for this URL
    ├── read vault: active-briefing.md + open lab notebook experiments
    ├── interview user (scope → adaptation → control → benchmark config)
    └── write new experiment .md to lab notebook

  Phase 2 — Implement (separate invocation after plan approval)
    ├── read plan from lab notebook
    ├── generate implementation code (allowed frameworks only)
    ├── run synthetic benchmark (control + implementation, weekly + monthly)
    ├── write README.md
    └── update experiment file (verdict, Papers:, results summary)
```

Alfred's addition is minimal: one extra write at step 4g (after marking ts as answered), appending to `paper-cache.json`:

```json
{
  "url": "https://arxiv.org/abs/...",
  "title": "...",
  "summary": "...",
  "methods_summary": "...",
  "connections": ["→ relevant to zero-inflated loss experiment"]
}
```

---

## Phase 1 — Interview & Plan

### Context Loading (before first question)

Read in parallel:
1. `~/.claude/skills/alfred/paper-cache.json` — find entry matching the provided URL
2. `~/ObsidianVault/DaybreakResearch/05-ClaudeContext/active-briefing.md`
3. All `.md` files in `~/ObsidianVault/DaybreakResearch/03-LabNotebook/` with `verdict: null` or absent — extract `hypothesis` frontmatter

If the URL is not in Alfred's cache, halt and tell the user: "This paper hasn't been processed by Alfred yet — ask Alfred about it first in #research-digest, then invoke /implement-paper."

### Interview Sequence

Questions are asked one at a time. The skill uses the loaded context to make each question specific, not generic.

**1. Scope**
> "Alfred summarized this as: [methods_summary]. Which part do you want to implement — the full method, a specific component (e.g. the loss function, the encoder), or an adaptation of it?"

**2. Existing experiment check** (only if Alfred flagged a connection)
> "Alfred connected this to [open hypothesis name]. Should this implementation extend that experiment or stand alone as a new one?"

**3. Framework mapping**
Based on scope answer, the skill proposes a concrete mapping:
> "The paper's [mechanism] maps to [specific MLForecast/NeuralForecast/etc. approach]. Here's the plan: [one-paragraph description]. Does this match your intent, or should we adjust?"

If the mechanism cannot be naturally expressed in the allowed stack, present two compliant alternatives before asking which to pursue.

**4. Control / Baseline**

The skill first tries to infer the control:
- Modifying a loss function → vanilla version of same model with default loss
- Modifying a model architecture → base architecture without the modification
- Novel method on standard problem → strongest available baseline in the allowed stack

If unambiguous, confirm:
> "I'll use [vanilla X] as the control baseline. Does that work?"

If **at all unclear**, enter a dedicated sub-interview:
> "I'm not confident what the right baseline is here. Tell me in natural language what you want to benchmark against."

Continue the sub-interview until the control spec is fully explicit: model name, configuration, and any relevant hyperparameters. The user must approve the control before the skill proceeds. **No implementation plan is written until the control is airtight.**

**5. Benchmark config**
> "Run weekly only, monthly only, or both? Standard metrics are RMSE, MAE, ME (bias), and wMAPE — any additions or changes?"

**6. Success criterion**
> "What result would mark this experiment as `verdict: confirmed`? (e.g., >5% MAE improvement on intermittent series over the control)"

### Plan Output

After all six steps are approved, the skill writes a new experiment file:

**Path:** `~/ObsidianVault/DaybreakResearch/03-LabNotebook/YYYY-MM-DD-<slug>.md`

```markdown
---
hypothesis: "[Scope answer, one sentence]"
verdict: null
papers: "[Title](url)"
---

## Implementation Plan

**Framework:** [chosen lib(s)]
**Control:** [exact control spec]
**Benchmark:** weekly + monthly, 10k series each
**Success criterion:** [from interview step 6]

### Method Mapping
[Paragraph from framework mapping step]

### Scope
[What is and isn't being implemented]

## Links
- Papers: [Title](url)
- Code: ~/DaybreakResearch/implementations/<slug>/
```

The skill then says: "Plan written to [path]. Review it and invoke `/implement-paper <url>` again to start Phase 2."

---

## Phase 2 — Implementation

Triggered by invoking `/implement-paper <url>` a second time. The skill detects an existing plan file for this URL and enters Phase 2.

### Output Artifacts

```
~/DaybreakResearch/implementations/<experiment-slug>/
  ├── benchmark_data.py   # synthetic data generator (shared module)
  ├── model.py            # core implementation (allowed frameworks only)
  ├── benchmark.py        # runs control + implementation, writes results.json
  ├── results.json        # raw metric output by series_type
  └── README.md           # paper details + benchmark results table
```

### Synthetic Benchmark

**Design goal:** Resemble the M5 dataset in behavior — noisy, low-signal retail series with realistic zero structure, promotional spikes, calendar effects, and heavy right-skew. Not a smooth academic benchmark.

**Series archetypes (10k series per frequency, split by proportion):**

| Type | Generation | Proportion |
|---|---|---|
| Intermittent | Bernoulli demand arrivals (p=0.2–0.4, M5-like zero density); non-zero magnitudes from lognormal; occasional promotional spikes 3–8× base | 30% |
| Heavy-tailed | Negative binomial with high dispersion; base demand low, periodic large bursts (event/holiday analog); right-skew matches M5 item-level distributions | 25% |
| Non-constant variance | Slow-moving trend (up or down) + multiplicative weekly/annual seasonality + ARCH-like noise bursts; variance scales with level | 25% |
| High-selling | High base volume, smooth trend, additive noise; lower CV but still noisy; represents steady top-sellers | 20% |

**Shared realism layers applied to all archetypes (M5-style):**
- **Holiday/event spikes:** ~8 randomly placed spike events per series per year (1.5–4× multiplier, decaying over 1–2 periods after)
- **Level shifts:** ~1–2 permanent step changes per series (item delisting / restock / store-open analog)
- **Price sensitivity analog:** random promotional periods with demand lift (not modeled as a feature, just baked into `y`)
- **Zero floor:** all values clipped to 0 — no negative demand
- **Integer demand:** final `y` values rounded to non-negative integers (M5 is unit-sales count data)

- **Weekly:** 10k series, 156 time points (~3 years), freq `W`
- **Monthly:** 10k series, 36 time points (~3 years), freq `MS`
- Output format: long (`unique_id`, `ds`, `y`, `series_type`) — native to all four libs
- Deterministic via fixed seed (reproducible across runs)
- `series_type` column preserved through to results so metrics can be sliced by archetype

**Evaluation metrics** (all reported per `series_type` and aggregate):

| Metric | Formula | Purpose |
|---|---|---|
| RMSE | √mean((ŷ−y)²) | Penalizes large errors; sensitive to spikes |
| MAE | mean(\|ŷ−y\|) | Robust central error |
| ME (bias) | mean(ŷ−y) | Signed bias; positive = over-forecast |
| wMAPE | Σ\|ŷ−y\| / Σy | Scale-free; handles zeros better than MAPE |

`benchmark.py` runs both the **control** and the **implementation** on identical train/test splits. Results table reports all four metrics for both runs plus Δ (implementation − control). Negative Δ = improvement for RMSE/MAE/wMAPE; ME Δ sign interpreted separately (direction of bias shift matters).

### README.md Structure

```markdown
# [Paper Title]

[1-paragraph summary sourced from Alfred's cache]

**Paper:** [url]
**Implemented:** [date]
**Frameworks:** [list]

## Method

[What was implemented and what was intentionally excluded from scope]

## Control Baseline

[Exact control spec agreed in interview]

## Results

### Weekly (10k series)
| Series Type | Control RMSE | Impl RMSE | Δ | Control MAE | Impl MAE | Δ | Control ME | Impl ME | Δ | Control wMAPE | Impl wMAPE | Δ |
|...

### Monthly (10k series)
| Series Type | Control RMSE | Impl RMSE | Δ | Control MAE | Impl MAE | Δ | Control ME | Impl ME | Δ | Control wMAPE | Impl wMAPE | Δ |

**Series mix:** 30% intermittent · 25% heavy-tailed · 25% non-constant variance · 20% high-selling

## Verdict

[success_criterion met / not met, one sentence]
```

### Experiment File Update

After benchmark completes, update the lab notebook entry:
- Set `verdict: confirmed` / `partial` / `refuted` based on success criterion
- Append results summary under a `## Results` section
- Confirm `Papers:` link is present

---

## Skill File

**Path:** `~/.claude/skills/implement-paper/SKILL.md`

Trigger: `/implement-paper <arxiv-url>`

The skill detects phase by grepping for the paper URL across all `.md` files in the lab notebook directory:
- No matching entry → Phase 1 (interview)
- Matching entry found with `verdict: null` → Phase 2 (implement)
- Matching entry found with a set verdict → inform user experiment is already complete, offer to start a new variant

**Experiment slug:** derived as `YYYY-MM-DD-<kebab-case-paper-title-first-5-words>`, e.g. `2026-05-02-zeroinflated-loss-for-nhits`. Used for both the lab notebook filename and the implementations directory name.

---

## Alfred Addition

In `alfred/SKILL.md`, after step 4g (mark as answered), add:

**4h. Write to paper cache**

Append to `~/.claude/skills/alfred/paper-cache.json`:

```json
{
  "url": "<paper url>",
  "title": "<paper title>",
  "summary": "<Alfred's answer text, trimmed to ~200 words>",
  "methods_summary": "<1–2 sentences on the core method>",
  "connections": ["<each → connection line Alfred generated, if any>"]
}
```

If the file doesn't exist, create it as a JSON array. If the URL already exists in the cache, skip (idempotent).

---

## What This Skill Does Not Do

- Fetch or analyze the paper — Alfred already did this
- Choose frameworks not in the allowed set without surfacing it in the interview
- Begin implementation before the control baseline is approved
- Skip the Phase 1 checkpoint — Phase 2 is always a separate invocation
