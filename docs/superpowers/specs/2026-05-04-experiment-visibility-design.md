# Experiment Visibility & Lineage Design Spec
_2026-05-04_

## Overview

Make benchmark findings a first-class citizen across the research flywheel. Two concerns addressed together:

1. **Lineage** — experiment artifacts (`results.json`, `model.py`, `README.md`) live off-device in GDrive, not just on the local machine.
2. **Visibility** — the existing weekly-review email gains a richer experiment section with actual metric deltas, GDrive links, and clear synthetic-vs-real categorization.

No new infrastructure. No MLflow. No S3. Uses GDrive (already wired up) and the existing weekly-review email pipeline.

---

## Skills Modified

| Skill | Change |
|---|---|
| `implement-paper` | Phase 2: upload artifacts to GDrive; add `data_source: synthetic` to experiment frontmatter |
| `log-experiment` | Add `data_source: real` to created frontmatter |
| `debrief` | Set `data_source: real` on any experiment it closes missing the field |
| `weekly-review` | Step 1: fetch `results.json` from GDrive; Step 4: restructured email experiment section |

---

## 1. Frontmatter — `data_source` field

All lab notebook `.md` files gain a `data_source` frontmatter field:

```yaml
---
hypothesis: "..."
verdict: null
papers: "[Title](url)"
data_source: synthetic   # or: real
---
```

**Who sets it:**

- `implement-paper` always sets `data_source: synthetic` when writing the Phase 1 plan file.
- `log-experiment` always sets `data_source: real` when pre-registering.
- `debrief` sets `data_source: real` on any experiment file it closes that is missing the field (backfill for existing entries).

**Inference rule for weekly-review** (handles files that predate this change):
- If `data_source` is missing and the file has a `papers:` frontmatter field → treat as `synthetic`.
- If `data_source` is missing and no `papers:` field → treat as `real`.

---

## 2. implement-paper Phase 2 — GDrive Artifact Upload

After the experiment file is updated (verdict written, results summary appended), add a final step:

### 2a. Upload artifacts

Using the GDrive MCP tools available in Claude Code, upload three files to GDrive:

| Local path | GDrive path |
|---|---|
| `~/DaybreakResearch/implementations/<slug>/results.json` | `DaybreakResearch/implementations/<slug>/results.json` |
| `~/DaybreakResearch/implementations/<slug>/model.py` | `DaybreakResearch/implementations/<slug>/model.py` |
| `~/DaybreakResearch/implementations/<slug>/README.md` | `DaybreakResearch/implementations/<slug>/README.md` |

Steps:
1. Check if folder `DaybreakResearch/implementations/<slug>` exists in GDrive — create it if not.
2. Upload each file. If a file already exists (re-run case), overwrite it.

### 2b. Record GDrive URL in experiment file

After uploading, retrieve the GDrive folder URL and append it to the `## Links` section of the lab notebook `.md`:

```markdown
## Links
- Papers: [Title](url)
- Code: ~/DaybreakResearch/implementations/<slug>/
- GDrive: https://drive.google.com/drive/folders/<folder-id>
```

### 2c. Upload failure handling

If any upload fails, print a warning but do not halt. The experiment is complete — GDrive upload is best-effort. Tell the user:
> "GDrive upload failed for `<slug>` — artifacts are still at `~/DaybreakResearch/implementations/<slug>/`. Re-run the upload manually or invoke `/implement-paper <url>` again to retry Phase 2."

---

## 3. weekly-review — Step 1 Changes

When gathering inputs, for each lab notebook `.md` with a non-null verdict in the past 7 days:

1. Read the `## Links` section and extract the `GDrive:` URL if present.
2. If GDrive URL is present: fetch `results.json` from GDrive using the MCP GDrive tools.
3. If GDrive URL is absent or fetch fails: fall back to local `~/DaybreakResearch/implementations/<slug>/results.json`.
4. If neither source yields `results.json`: record the experiment with verdict only, no metric row.

Parse `results.json` to extract the **top improvement**: the single largest absolute delta in wMAPE across all series types and horizons where the implementation beat the control. If the experiment was refuted, use the largest regression instead (shown as a positive number with a `+` sign).

---

## 4. weekly-review — Step 4 Email Changes

Replace the simple experiment table with three labelled sections. Only include experiments with verdicts set in the past 7 days.

### Section: ⚗️ Synthetic benchmarks

Header line (always present):
```
⚗️ Synthetic benchmarks — M5-style · 10k series · not yet validated on production data
```

Table:
```
| Experiment | Verdict | Top improvement | Series type | |
|---|---|---|---|---|
| <slug> | ✅ / ⚠️ / ❌ | −11.2% wMAPE · h=8 | intermittent | GDrive ↗ |
```

- `Top improvement` is formatted as `[±][value]% [metric] · h=[horizon]`.
- If `results.json` was unavailable, show `—` in the Top improvement and Series type columns.
- GDrive link opens the experiment folder. If no GDrive URL, omit the link cell.

### Section: 📊 Real data results

```
| Experiment | Verdict | Key result | Project | |
|---|---|---|---|---|
| <slug> | ✅ / ⚠️ / ❌ | <verdict sentence from .md> | <project> | GDrive ↗ |
```

- `Key result` is pulled from the one-sentence verdict in the experiment `.md` `## Results` section.
- `Project` is inferred from the hypothesis or daily note context.
- If no experiments with `data_source: real` closed this week, omit this section entirely.

### Section: 🔬 Should test on real data

Auto-generated list. Include any lab notebook entry where ALL of:
- `data_source: synthetic`
- `verdict: confirmed` OR `verdict: partial`
- No matching lab notebook entry exists with `data_source: real` whose slug shares ≥2 of the first 5 words with the synthetic entry's slug

Format:
```
🔬 Should test on real data
  • <slug> — <one-line hypothesis from frontmatter> (<verdict>, synthetic)
```

If the list is empty, omit this section.

### Section: ⏳ In progress

List all lab notebook entries (any `data_source`) where `verdict: null`, updated in the past 14 days:
```
⏳ In progress
  • <slug> (synthetic · started <date>)
  • <slug> (real · started <date>)
```

### Full email example

```
Experiment results

⚗️ Synthetic benchmarks — M5-style · 10k series · not yet validated on production data

| Experiment | Verdict | Top improvement | Series type | |
|---|---|---|---|---|
| 2026-05-02-zeroinflated-loss-nhits | ✅ confirmed | −11.2% wMAPE · h=8 | intermittent | GDrive ↗ |
| 2026-05-03-arch-noise-nhits | ❌ refuted | +2.8% wMAPE · h=4 | non_constant_variance | GDrive ↗ |

📊 Real data results

| Experiment | Verdict | Key result | Project | |
|---|---|---|---|---|
| fourthroot-hasbro-v7 | ✅ confirmed | −5.1% wMAPE vs sqrt on Hasbro holdout | Hasbro | — |

🔬 Should test on real data
  • 2026-05-02-zeroinflated-loss-nhits — zero-inflated loss for NHITS confirmed −11.2% wMAPE on intermittent (synthetic)

⏳ In progress
  • 2026-05-03-tweedie-loss-mlforecast (synthetic · started 2026-05-03)
```

---

## 5. What This Does Not Do

- Does not introduce MLflow, W&B, or any experiment tracking server.
- Does not query GDrive for historical experiments outside the past 7 days (weekly-review scope is unchanged).
- Does not automatically promote a synthetic experiment to a real one — that remains a manual `/log-experiment` + `/debrief` flow.
- Does not block the weekly-review email if GDrive is unreachable — falls back to local files.
