---
name: create-experiment-documentation
description: Use when setting up a new Confluence page for an experiment with standardized structure under DS R&D
---

# Create Experiment Documentation

## Overview

Creates a new Confluence page under the DS R&D parent with a type-specific experiment template. **NEW:** When provided code, first generates a production-oriented README.md explaining the algorithm, then uses that README to guide template selection and pre-fill sections. Automatically adapts structure based on experiment type (model comparison, parameter tuning, ablation study, production investigation).

## When to Use

**Use when:**
- Starting a new experiment (ML model comparison, feature test, POC, hyperparameter tuning, investigation)
- You want consistent experiment documentation across projects
- Multiple people will reference the same experiment
- You need to track hypotheses vs actual results

**Provide:**
- Experiment name/title
- Brief objective (1-2 sentences)
- **Optional: Code** (Python, notebook, script — if provided, skip to Code-to-README Phase below)
- **Experiment type** (if no code; otherwise inferred from README)

---

## CODE-TO-README PHASE (Optional but Recommended)

**If you have code to document, provide it now.** This phase generates a production README that clarifies what the code does before creating the experiment template. Saves guessing and pre-fills sections.

### Workflow

1. **You provide:** Code file(s), notebook, or script
2. **I generate:** `README.md` (5-8 bullet points) explaining:
   - **What:** Algorithm/approach (e.g., "Exponential smoothing with MSTL seasonal decomposition")
   - **Why:** Problem it solves (e.g., "Improves forecast accuracy on retail demand with strong seasonality")
   - **How:** Key components (decomposition, optimization method, prediction logic)
   - **Params:** What's being optimized (e.g., "α (smoothing) & β (trend damping) via grid search")
   - **Data:** Domain and scope (e.g., "Retail demand: 210 series × 7 demand patterns")
   - **Evaluation:** How it's tested (e.g., "MAE/RMSE comparison vs V9 baseline")
   - **Key improvements:** List of 3-5 enhancements (e.g., "MSTL decomposition, horizon-adaptive α, cold-start guard")

3. **README informs template type:**
   - `"params being optimized"` → **Type 2: Parameter Tuning**
   - `"comparing 2+ models/approaches"` → **Type 1: Model Comparison**
   - `"testing features/components"` → **Type 3: Ablation Study**
   - `"debugging between environments"` → **Type 4: Production Investigation**

4. **I pre-fill sections using README:**
   - **Objective:** From README's "What/Why"
   - **Setup/Configurations:** From README's "How"
   - **Success Criteria:** From README's evaluation strategy
   - **Key improvements/Features:** From README's feature list

5. **Result:** Experiment template with context-aware pre-filled sections (not blank guesses)

### Example: README Generated from Code

```markdown
# MarkovianTheta v10: Production README

**What:** Exponential smoothing with MSTL seasonal decomposition and grid-search parameter optimization.

**Why:** Improves forecast accuracy on retail demand data with strong seasonal patterns and trend changes.

**How:** 
- Decomposes input series into trend, seasonal, residual components using MSTL
- Optimizes smoothing level (α) and trend damping (β) via exhaustive grid search
- Generates point forecasts + conformal prediction intervals
- Falls back to OptimizedTheta for cold-start series (n < 30)

**Params Optimized:** 
- α (smoothing): [0.01, 0.50] × 20 steps
- β (trend damping): [0.01, 0.30] × 15 steps
- Total: 300 configurations

**Data:** Retail demand forecasting (210 time series × 7 demand patterns: trend, seasonal, level-shift, intermittent, pure-seasonal, trend-only, noise)

**Evaluation:** MAE vs V9 baseline; tested on hold-out set; analyzed by demand type

**Key Improvements:**
1. MSTL seasonal decomposition (vs simple seasonal_decompose)
2. Horizon-adaptive smoothing α(h)
3. CUSUM level-shift detection
4. Cold-start guard (fallback to OptimizedTheta)
5. Conformal prediction intervals (lo-95, hi-95)
```

**After README is generated:** Proceed to Routing Question below with context from the README guiding your answer.

---

## ROUTING QUESTION - Answer This First

**What type of experiment is this?**

### **Type 1: Model Comparison**
- Testing 2+ models/approaches side-by-side
- Example: DLinear vs LSTM, with/without features, model A vs model B
- Use when: Deciding which model to use, benchmarking approaches

### **Type 2: Parameter Tuning**
- Optimizing a single model's parameters across 3+ values
- Example: α ∈ {0.1, 0.2, 0.3, 0.4, 0.5}, learning_rate grid search
- Use when: Finding optimal hyperparameters, sensitivity analysis

### **Type 3: Ablation / Feature Study**
- Testing components or features of one model
- Example: with/without weather data, adding/removing ensemble members
- Use when: Validating feature importance, testing specific hypotheses

### **Type 4: Production Investigation**
- Debugging/validating a model across environments
- Example: notebook vs production drift, pre-deployment validation
- Use when: Troubleshooting performance gaps, validating deployments

---

## Template by Type

### **Type 1: Model Comparison**

```markdown
# [Experiment Name]

**Experiment Type:** Model Comparison
**Owner:** @[Your Name]
**Date Started:** YYYY-MM-DD
**Status:** In Progress | Complete | On Hold | Blocked

---

## Objective
[Which model performs better? Under what conditions?]

---

## Setup

[Data scope, both model configs, success criteria]

### Model Configurations

| Model | Configuration |
|-------|---------------|
| **Baseline** | [config] |
| **New Model** | [config] |

**Success Criteria:**
- Model achieves ≥X% improvement in [metric]
- Consistent performance across [condition]
- [Any other requirements]

---

## Findings

_Results pending_

### Metrics Summary

| Customer/Series | Baseline WMAPE+\|B\| | Baseline RMSE | Baseline RMSSE | Model WMAPE+\|B\| | Model RMSE | Model RMSSE | Winner |
|---|---|---|---|---|---|---|---|
| Series 1 | - | - | - | - | - | - | |
| Series 2 | - | - | - | - | - | - | |
| Average | - | - | - | - | - | - | ✓ |

### Interpretation

[Which model won? By how much? Any caveats?]

---

## Notebook & Code

- **Baseline Model:** [Link]
- **New Model:** [Link]
- **Training Script:** [Link]
- **Analysis:** [Link]

---

## Links

[References and related work]

---

## Next Steps

- [ ] Train both models
- [ ] Compute metrics on all series
- [ ] Analyze improvement distribution
- [ ] If new model wins: Validate on hold-out set
- [ ] If baseline wins: Investigate why, document learnings
- [ ] Document best model and deployment plan
```

---

### **Type 2: Parameter Tuning**

```markdown
# [Experiment Name]

**Experiment Type:** Parameter Tuning
**Owner:** @[Your Name]
**Date Started:** YYYY-MM-DD
**Status:** In Progress | Complete | On Hold | Blocked

---

## Objective
[What parameter? What range? What's optimal?]

---

## Setup

[Model config, parameter range, data scope, tuning approach]

**Parameters Tested:** [e.g., α ∈ {0.1, 0.2, 0.3, 0.4, 0.5}]
**Base Model:** [config]
**Metric:** [primary metric for optimization]

**Success Criteria:**
- Identify clear winner with [X]% improvement over default
- Selected value shows consistency across [condition]

---

## Findings

_Results pending_

### Metrics Summary (Aggregated)

| Parameter Value | Avg WMAPE+\|B\| | Avg RMSE | Avg RMSSE | Best? |
|---|---|---|---|---|
| Value 1 | - | - | - | |
| Value 2 | - | - | - | ✓ |
| Value 3 | - | - | - | |

### Per-Series/Customer Breakdown

| Parameter | Series 1 | Series 2 | Series 3 | Consistency |
|---|---|---|---|---|
| Value 1 | - | - | - | |
| Value 2 | - | - | - | ✓ |
| Value 3 | - | - | - | |

### Interpretation

[Which value performed best? Consistent across all conditions?]

---

## Notebook & Code

- **Tuning Script:** [Link to parameter sweep]
- **Analysis & Visualization:** [Link to results]

---

## Links

[Theory, references, related experiments]

---

## Next Steps

- [ ] Test parameter values across all conditions
- [ ] Compute metrics for each value
- [ ] Identify best performer
- [ ] If clear winner: Validate on hold-out set, deploy
- [ ] If tied/unclear: Test additional range, investigate why
- [ ] Document selected value and rationale
```

---

### **Type 3: Ablation / Feature Study**

```markdown
# [Experiment Name]

**Experiment Type:** Ablation / Feature Study
**Owner:** @[Your Name]
**Date Started:** YYYY-MM-DD
**Status:** In Progress | Complete | On Hold | Blocked

---

## Objective
[What component/feature? Does it help or hurt?]

---

## Setup

[Base model, what's being added/removed, data scope]

**Grouping Dimension:** [By category? By region? By customer type?]

**Feature/Component:** [Description]

### Model Configurations

| Configuration | Details |
|---|---|
| **Baseline** | [without feature] |
| **Enhanced** | [with feature] |

**Success Criteria:**
- Helps on [specific groups]: ≥X% improvement
- No degradation on [specific groups]: ≤Y% change
- Overall impact: [target]

---

## Findings

_Results pending_

### Metrics Summary (Grouped by [DIMENSION])

| [Dimension] | Without Feature | With Feature | Improvement | Status | Notes |
|---|---|---|---|---|---|
| Group A | - | - | - | Pending | |
| Group B | - | - | - | Pending | |
| Overall | - | - | - | Pending | |

### Interpretation

[Does feature help? On which groups? Any negative effects?]

---

## Notebook & Code

- **Feature Engineering:** [Link]
- **Model Training:** [Link]
- **Analysis:** [Link]

---

## Links

[Feature source, related experiments]

---

## Next Steps

- [ ] Implement feature/component
- [ ] Train baseline and enhanced models
- [ ] Compute metrics by [dimension]
- [ ] Analyze feature importance
- [ ] If helps on target groups: Integrate permanently
- [ ] If hurts on any group: Investigate root cause
- [ ] If mixed: Enable selectively by group
- [ ] Document findings and deployment plan
```

---

### **Type 4: Production Investigation**

```markdown
# [Experiment Name]

**Experiment Type:** Production Investigation
**Owner:** @[Your Name]
**Date Started:** YYYY-MM-DD
**Status:** In Progress | Complete | On Hold | Blocked

---

## Objective
[What's the discrepancy? Why does [condition A] differ from [condition B]?]

---

## Setup

[Environment comparison, testing scope, root cause hypotheses]

**Environments/Scenarios:**
- Environment A: [description]
- Environment B: [description]

**Test Scope:** [details]

**Hypotheses:**
- [Possible cause 1]
- [Possible cause 2]
- [Possible cause 3]

---

## Findings

_Investigation in progress_

### Diagnostic Checklist

| Diagnostic | Environment A | Environment B | Match? | Status |
|---|---|---|---|---|
| [Check 1] | - | - | - | Pending |
| [Check 2] | - | - | - | Pending |
| [Check 3] | - | - | - | Pending |

### Performance Comparison

| Metric | Environment A | Environment B | Gap | Root Cause |
|---|---|---|---|---|
| [Metric 1] | - | - | - | Pending |
| [Metric 2] | - | - | - | Pending |

### Root Cause Analysis

**Hypothesis:** [What you think is wrong]
**Evidence:** [What you found]
**Root Cause Identified:** [Actual issue]
**Fix Applied:** [Solution]
**Validation:** [How you confirmed]

---

## Notebook & Code

- **Comparison Script:** [Link]
- **Diagnostics:** [Link]
- **Validation:** [Link]

---

## Links

[Deployment logs, documentation, related systems]

---

## Next Steps

- [ ] Extract representative sample from both environments
- [ ] Run diagnostics on sample
- [ ] Compare outputs at each preprocessing step
- [ ] Identify first divergence point
- [ ] Investigate root cause
- [ ] Implement fix
- [ ] Validate fix in both environments
- [ ] Deploy fix
- [ ] Verify performance gap closed
- [ ] Document preventive measures
```

---

## Decision Tree

```
START: What type of experiment?
├─ Comparing 2+ models? → Type 1 (Model Comparison)
├─ Testing 3+ parameter values? → Type 2 (Parameter Tuning)
├─ Testing features/components? → Type 3 (Ablation)
├─ Debugging between environments? → Type 4 (Investigation)
└─ Other → Default to Type 1 or clarify with user
```

## Implementation

**Enhanced Workflow:**

**IF code is provided:**
1. Ask user: "Do you want me to analyze your code first?"
2. Generate production README.md (5-8 bullets) explaining algorithm, params, evaluation strategy
3. Use README to infer experiment type (e.g., "params being optimized" → Type 2)
4. Pre-fill experiment template using README context (no blanks or guesses)
5. Show README + filled template for user review
6. Return Confluence page link with customized sections

**IF no code is provided:**
1. Ask user: "What type of experiment: comparison, tuning, ablation, or investigation?"
2. User selects type (or describes)
3. Generate appropriate template structure
4. Pre-fill with standard sections for that type
5. Return Confluence page link with customized metrics table

## Quick Reference

| Question | Type 1 | Type 2 | Type 3 | Type 4 |
|----------|--------|--------|--------|--------|
| "How many things?" | 2+ models | 3+ param values | 1 model + variations | 1 model + environments |
| "Table structure?" | Models vs metrics | Params vs metrics | Groups vs features | Diagnostics |
| "Success metric?" | % improvement | Clear winner | Per-group impact | Gap explanation |
| "Next steps" | Decision branches | Linear sequence | Conditional branches | Linear diagnostic |

## Common Mistakes

**When SKIPPING code analysis:**
- ❌ Guessing what the code does → filling sections with assumptions that may be wrong
- ❌ Relying on external context (memory, other docs) → template missing critical details
- ❌ Leaving sections blank with "pending" → loses opportunity to pre-fill from code
- ❌ Wrong type selection without code clarity → template structure doesn't fit algorithm
- ❌ No improvements list → readers can't understand what was actually added

**General (all cases):**
- ❌ Not specifying experiment type → template mismatch
- ❌ Vague success criteria → ambiguous winning condition
- ❌ Wrong table structure for type → confusion
- ❌ Missing grouping dimension (Type 3) → unclear results
- ❌ Mixing investigation with comparison → incompatible templates

## Pro Tips

1. **Always provide code if available:** Code-to-README phase pre-fills sections and prevents guessing. 5-minute README generation saves 20 minutes of blank-filling later.
2. **README as artifact:** Keep the generated README in your documentation or wiki. It becomes the canonical source for "what does this algorithm do?"
3. **Type selection is easier with code:** Algorithm description clarifies whether it's tuning (3+ params), comparison (2+ models), ablation (1 model + features), or investigation (1 model + environments).
4. **Before creating page:** If no code, spend 30 seconds deciding type. If code, let the README decide for you.
5. **Success criteria:** Be specific. "≥5%" is better than "significant improvement"
6. **Grouping dimension:** Decide upfront (by category? region? customer?). Hard to change mid-experiment.
7. **Notebook links:** Link early and often. Future you will thank you.
8. **Next steps:** Make them decision-branched (if/then). Guides follow-up work.
