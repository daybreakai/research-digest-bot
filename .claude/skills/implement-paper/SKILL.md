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
data_source: synthetic
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

<One block per freq × horizon. Lead each block with a one-sentence "does it work?" verdict, then the delta table. Example:>

### Weekly · h=4 (3 folds, avg)

wMAPE down −2.2% overall; bias clean (ΔME = −0.9).

| Series Type | Δ wMAPE | Δ MAE | Δ ME |
|---|---|---|---|
| intermittent | −5.2% | −3.4 | −0.1 |
| heavy_tailed | −1.2% | −0.8 | +0.3 |
| non_constant_variance | +0.3% | +0.2 | −0.1 |
| high_selling | −2.1% | −1.4 | +0.2 |
| ALL | −2.2% | −1.4 | +0.1 |

<repeat for each horizon × frequency>

**Series mix:** 30% intermittent · 25% heavy-tailed · 25% non-constant variance · 20% high-selling
**CV:** equally spaced folds, step_size=h, metrics averaged across folds

## Verdict

<one sentence: success_criterion from plan — met / partially met / not met, with the key number>
```

Fill every table cell from `results.json`. No placeholders.
- Express Δ wMAPE as a percentage change rounded to 1 decimal (e.g. "−2.2%"), not a raw decimal
- Round Δ MAE and Δ ME to 1 decimal place
- The one-sentence block lead should call out the ALL-row Δ wMAPE and whether bias (ΔME) is clean or problematic

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

| freq · h · pair | Δ wMAPE | Δ MAE | Δ ME |
|---|---|---|---|
<fill from results.json, ALL rows only — one row per key, Δ wMAPE as %, Δ MAE and Δ ME to 1 decimal>
```

### GDrive Artifact Upload

After the experiment file is updated, upload three artifacts to GDrive using the GDrive MCP tools available in Claude Code. This is best-effort — a failure here does not invalidate the experiment.

**Step 1 — Create folder**

Search GDrive for a folder named `<slug>` inside `DaybreakResearch/implementations/`. If it does not exist, create it at that path.

**Step 2 — Upload files**

Upload each of the following. If a file already exists in the folder, overwrite it:

| Local path | GDrive filename |
|---|---|
| `~/DaybreakResearch/implementations/<slug>/results.json` | `results.json` |
| `~/DaybreakResearch/implementations/<slug>/model.py` | `model.py` |
| `~/DaybreakResearch/implementations/<slug>/README.md` | `README.md` |

**Step 3 — Record the folder URL**

After uploading, get the GDrive folder's shareable URL. Edit the `## Links` section of `~/ObsidianVault/DaybreakResearch/03-LabNotebook/<slug>.md` to add a GDrive line:

```markdown
## Links
- Papers: [<paper title>](<url>)
- Code: ~/DaybreakResearch/implementations/<slug>/
- GDrive: https://drive.google.com/drive/folders/<folder-id>
```

**Step 4 — Failure handling**

If any upload step fails, do not halt the skill. Print:
> "GDrive upload failed for `<slug>` — artifacts are still at `~/DaybreakResearch/implementations/<slug>/`. Invoke `/implement-paper <url>` again to retry Phase 2."

Then continue to the "Writing Back to the Flywheel" step.

### Writing Back to the Flywheel

After setting the verdict, if the result is `confirmed` or `partial`, close the loop for Alfred and research-brief:

**1. Append to active-briefing.md**

Read `~/ObsidianVault/DaybreakResearch/05-ClaudeContext/active-briefing.md`. Append a brief note at the end:

```markdown
## Experiment Feedback — <slug> (<date>)

**Verdict:** <confirmed/partial>
**What worked:** <1–2 sentences: what technique, on which series types, at what horizons — use the actual numbers>
**Related areas to watch:** <3–5 comma-separated topic phrases, e.g. "sparse demand modeling, count data distributions, loss function design for intermittent demand">
```

Keep it short — the goal is to prime Alfred for related papers, not to restate the full results.

**2. Suggest research-brief topic weight updates**

Tell the user:
> "The related areas from this experiment are: [list]. Would you like me to bump the weights on these topics in research-brief? I can call `save_user_prefs` to increase their weight so future digests surface more of this."

If the user says yes, read the current prefs via `get_user_prefs`, increase matching keywords by 0.3 (cap at 2.0), add any new keywords at weight 1.3, and call `save_user_prefs` with the updated array.

If `verdict: refuted`, skip this step entirely — no signal to propagate.

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
