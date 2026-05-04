# Experiment Visibility & Lineage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make benchmark findings first-class by tagging experiment data sources, uploading artifacts to GDrive after each benchmark, and restructuring the weekly-review email with synthetic/real categorization and real metric deltas.

**Architecture:** Four skill files are edited (markdown only, no Python changes). `implement-paper` gains a `data_source: synthetic` frontmatter tag and a GDrive upload step. `log-experiment` and `debrief` gain `data_source: real`. `weekly-review` gains GDrive-aware results fetching and a four-section email experiment block.

**Tech Stack:** Markdown skill files, GDrive MCP tools (already available in Claude Code), existing weekly-review Gmail pipeline.

---

## File Map

| File | Change |
|---|---|
| `~/.claude/skills/implement-paper/SKILL.md` | Add `data_source: synthetic` to Phase 1 frontmatter template; add GDrive upload section in Phase 2 |
| `~/.claude/skills/log-experiment/SKILL.md` | Add `data_source: real` to Step 2 Set block |
| `~/.claude/skills/debrief/SKILL.md` | Add `data_source: real` backfill to Step 2 experiments block |
| `~/.claude/skills/weekly-review/SKILL.md` | Extend Step 1 with results.json fetch logic; replace Step 4 experiment table with four-section format |

---

### Task 1: implement-paper — `data_source: synthetic` in Phase 1 frontmatter

**Files:**
- Modify: `~/.claude/skills/implement-paper/SKILL.md` (around the Phase 1 plan template block, lines ~130–135)

- [ ] **Step 1: Read the current frontmatter template block**

Run: `grep -n "verdict: null\|papers:\|hypothesis:" ~/.claude/skills/implement-paper/SKILL.md`

Locate the plan template block that currently reads:
```
---
hypothesis: "<scope answer distilled to one sentence>"
verdict: null
papers: "[<paper title>](<url>)"
---
```

- [ ] **Step 2: Add `data_source: synthetic` to the template**

Edit `~/.claude/skills/implement-paper/SKILL.md`. Replace the frontmatter block:

```markdown
---
hypothesis: "<scope answer distilled to one sentence>"
verdict: null
papers: "[<paper title>](<url>)"
---
```

With:

```markdown
---
hypothesis: "<scope answer distilled to one sentence>"
verdict: null
data_source: synthetic
papers: "[<paper title>](<url>)"
---
```

- [ ] **Step 3: Verify the edit**

Run: `grep -A6 "hypothesis:.*scope answer" ~/.claude/skills/implement-paper/SKILL.md`

Expected output includes `data_source: synthetic` between `verdict: null` and `papers:`.

- [ ] **Step 4: Commit**

```bash
git add ~/.claude/skills/implement-paper/SKILL.md
git commit -m "feat: add data_source: synthetic to implement-paper frontmatter template"
```

---

### Task 2: implement-paper — GDrive artifact upload in Phase 2

**Files:**
- Modify: `~/.claude/skills/implement-paper/SKILL.md` (after "Updating the Experiment File" section, before "Writing Back to the Flywheel")

- [ ] **Step 1: Find the insertion point**

Run: `grep -n "Updating the Experiment File\|Writing Back to the Flywheel" ~/.claude/skills/implement-paper/SKILL.md`

The new section goes after the `### Updating the Experiment File` block ends and before `### Writing Back to the Flywheel`.

- [ ] **Step 2: Insert the GDrive upload section**

Edit `~/.claude/skills/implement-paper/SKILL.md`. Find the line:

```
### Writing Back to the Flywheel
```

Insert the following block immediately before it (separated by a blank line):

```markdown
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

```

- [ ] **Step 3: Verify the section is in place**

Run: `grep -n "GDrive Artifact Upload\|Writing Back to the Flywheel\|Updating the Experiment File" ~/.claude/skills/implement-paper/SKILL.md`

Expected: lines appear in order — `Updating the Experiment File` first, then `GDrive Artifact Upload`, then `Writing Back to the Flywheel`.

- [ ] **Step 4: Commit**

```bash
git add ~/.claude/skills/implement-paper/SKILL.md
git commit -m "feat: add GDrive artifact upload step to implement-paper Phase 2"
```

---

### Task 3: log-experiment — `data_source: real`

**Files:**
- Modify: `~/.claude/skills/log-experiment/SKILL.md` (Step 2, Set block, lines ~33–36)

- [ ] **Step 1: Read the current Step 2 Set block**

Run: `grep -n -A8 "## Step 2" ~/.claude/skills/log-experiment/SKILL.md`

The block currently reads:
```
Use _template-experiment.md. Set:
  verdict: null
  status: pre-registered
  date: today
```

- [ ] **Step 2: Add `data_source: real`**

Edit `~/.claude/skills/log-experiment/SKILL.md`. Replace:

```
Use _template-experiment.md. Set:
  verdict: null
  status: pre-registered
  date: today
```

With:

```
Use _template-experiment.md. Set:
  verdict: null
  status: pre-registered
  data_source: real
  date: today
```

- [ ] **Step 3: Verify**

Run: `grep -A6 "Use _template-experiment.md" ~/.claude/skills/log-experiment/SKILL.md`

Expected: `data_source: real` appears between `status: pre-registered` and `date: today`.

- [ ] **Step 4: Commit**

```bash
git add ~/.claude/skills/log-experiment/SKILL.md
git commit -m "feat: add data_source: real to log-experiment frontmatter"
```

---

### Task 4: debrief — `data_source: real` backfill

**Files:**
- Modify: `~/.claude/skills/debrief/SKILL.md` (Step 2 experiments block, around line ~38–39)

- [ ] **Step 1: Read the current experiments block in Step 2**

Run: `grep -n -A6 "IF experiments" ~/.claude/skills/debrief/SKILL.md`

The relevant lines currently read:
```
  → Set verdict frontmatter: confirmed | rejected | partial | null
  → If verdict is rejected → also create/append to
```

- [ ] **Step 2: Add the backfill line**

Edit `~/.claude/skills/debrief/SKILL.md`. Replace:

```
  → Set verdict frontmatter: confirmed | rejected | partial | null
  → If verdict is rejected → also create/append to
```

With:

```
  → Set verdict frontmatter: confirmed | rejected | partial | null
  → Set data_source: real if the field is absent in the file (backfill — do not overwrite existing value)
  → If verdict is rejected → also create/append to
```

- [ ] **Step 3: Verify**

Run: `grep -n "data_source\|verdict frontmatter\|verdict is rejected" ~/.claude/skills/debrief/SKILL.md`

Expected: `data_source: real` line appears between the verdict line and the rejected → FailureMuseum line.

- [ ] **Step 4: Commit**

```bash
git add ~/.claude/skills/debrief/SKILL.md
git commit -m "feat: add data_source: real backfill to debrief skill"
```

---

### Task 5: weekly-review — Step 1 results.json fetch

**Files:**
- Modify: `~/.claude/skills/weekly-review/SKILL.md` (Step 1 section, after the current file list)

- [ ] **Step 1: Read the current Step 1 block**

Run: `grep -n -A20 "## Step 1" ~/.claude/skills/weekly-review/SKILL.md`

Step 1 currently ends with the file list (daily notes, active-briefing, FailureMuseum, decision logs, evergreen stubs).

- [ ] **Step 2: Append the results fetch sub-step**

Edit `~/.claude/skills/weekly-review/SKILL.md`. Find the end of the Step 1 file list (the line reading `  - Any 02-EvergreenKnowledge stubs under 150 words (excluding frontmatter)`) and insert immediately after it:

```markdown

Also, for each lab notebook `.md` file that has a non-null verdict AND whose date field falls within the past 7 days:

1. Read its `data_source` frontmatter field. If missing: treat as `synthetic` if a `papers:` field is present, otherwise treat as `real`.
2. Read its `## Links` section and extract the `GDrive:` URL if present.
3. If `data_source: synthetic`:
   a. If a GDrive URL is present, fetch `results.json` from that GDrive folder using the GDrive MCP tools.
   b. If GDrive fetch fails or no URL, fall back to local `~/DaybreakResearch/implementations/<slug>/results.json`.
   c. If neither source yields `results.json`, record the experiment with verdict only (no metric data).
   d. From `results.json`, extract the **top improvement**: the single largest absolute Δ wMAPE value across all `series_type` × `h` combinations where `impl_wmape < ctrl_wmape`. Format: `−{value}% wMAPE · h={h}`. If the experiment was refuted (no improvement anywhere), use the largest regression: `+{value}% wMAPE · h={h}`. Also record the `series_type` that produced this result.
4. If `data_source: real`, extract the one-sentence verdict from the `## Results` section of the experiment `.md` file. Also extract the project name from the hypothesis frontmatter or daily note context.

Carry all extracted data forward as `experiment_records` for use in Step 4.
```

- [ ] **Step 3: Verify**

Run: `grep -n "top improvement\|experiment_records\|GDrive URL\|data_source" ~/.claude/skills/weekly-review/SKILL.md`

Expected: all four terms appear, all in the Step 1 block.

- [ ] **Step 4: Commit**

```bash
git add ~/.claude/skills/weekly-review/SKILL.md
git commit -m "feat: weekly-review Step 1 fetches results.json and data_source from lab notebook"
```

---

### Task 6: weekly-review — Step 4 email experiment section

**Files:**
- Modify: `~/.claude/skills/weekly-review/SKILL.md` (Step 4, experiment results section and HTML template)

This is the largest edit. It replaces the single experiment table with four labelled sections and updates the HTML template to match.

- [ ] **Step 1: Locate the current experiment results section in Step 4**

Run: `grep -n "Experiment results\|Project | Test\|<th.*Project\|<th.*Test" ~/.claude/skills/weekly-review/SKILL.md`

The current prose spec line is:
```
  3. **Experiment results** — table: Project | Test | Result | Status
     Only include confirmed / rejected / partial — skip null/open
```

And the HTML template contains a table with `Project`, `Test`, `Result`, `Status` headers.

- [ ] **Step 2: Replace the prose experiment results line in Step 4**

Edit `~/.claude/skills/weekly-review/SKILL.md`. Replace:

```
  3. **Experiment results** — table: Project | Test | Result | Status
     Only include confirmed / rejected / partial — skip null/open
```

With:

```
  3. **Experiment results** — four sections built from `experiment_records` (populated in Step 1). Only include experiments with verdicts set in the past 7 days.

     **⚗️ Synthetic benchmarks** (always present if any synthetic experiments this week):
     Header line: `⚗️ Synthetic benchmarks — M5-style · 10k series · not yet validated on production data`
     Table columns: `Experiment | Verdict | Top improvement | Series type | (GDrive link)`
     - Verdict: ✅ confirmed · ⚠️ partial · ❌ refuted
     - Top improvement: `−11.2% wMAPE · h=8` format (from `results.json`); `—` if unavailable
     - Series type: the series_type that produced the top improvement; `—` if unavailable
     - GDrive link: `GDrive ↗` linked to the folder URL; omit cell if no URL
     - Omit this section entirely if no synthetic experiments closed this week

     **📊 Real data results** (omit if no real experiments closed this week):
     Table columns: `Experiment | Verdict | Key result | Project | (GDrive link)`
     - Key result: one-sentence verdict from the experiment `.md` `## Results` section
     - Project: inferred from hypothesis or daily note

     **🔬 Should test on real data** (omit if empty):
     Auto-generated bulleted list. Scan ALL lab notebook `.md` files (not just this week's). Include every entry where:
     - `data_source: synthetic` (or inferred as synthetic: has `papers:` field, no `data_source` set)
     - `verdict: confirmed` or `verdict: partial`
     - No `data_source: real` lab notebook entry exists whose slug shares ≥2 of the first 5 words with this entry's slug
     Format: `• <slug> — <hypothesis> (<verdict>, synthetic)`

     **⏳ In progress** (omit if none):
     Bulleted list of all lab notebook entries with `verdict: null`, last modified within 14 days.
     Format: `• <slug> (synthetic · started <date>)` or `• <slug> (real · started <date>)`
```

- [ ] **Step 3: Replace the HTML template experiment table**

In `~/.claude/skills/weekly-review/SKILL.md`, find the HTML `<table>` block inside the email template (currently has `Project`, `Test`, `Result`, `Status` `<th>` headers). Replace the entire table block plus its `<h3>` header with:

```html
  <h3 style="margin-top:24px">Experiment results</h3>

  <!-- ⚗️ Synthetic benchmarks (omit section if no synthetic experiments this week) -->
  <p style="font-size:12px;color:#666;margin-bottom:4px">⚗️ Synthetic benchmarks — M5-style · 10k series · not yet validated on production data</p>
  <table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:16px">
    <tr style="background:#f5f5f5">
      <th style="padding:6px 8px;text-align:left">Experiment</th>
      <th style="padding:6px 8px;text-align:left">Verdict</th>
      <th style="padding:6px 8px;text-align:left">Top improvement</th>
      <th style="padding:6px 8px;text-align:left">Series type</th>
      <th style="padding:6px 8px;text-align:left"></th>
    </tr>
    {synthetic_rows}
  </table>

  <!-- 📊 Real data results (omit section if no real experiments this week) -->
  <p style="font-size:13px;font-weight:bold;margin-bottom:4px">📊 Real data results</p>
  <table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:16px">
    <tr style="background:#f5f5f5">
      <th style="padding:6px 8px;text-align:left">Experiment</th>
      <th style="padding:6px 8px;text-align:left">Verdict</th>
      <th style="padding:6px 8px;text-align:left">Key result</th>
      <th style="padding:6px 8px;text-align:left">Project</th>
      <th style="padding:6px 8px;text-align:left"></th>
    </tr>
    {real_rows}
  </table>

  <!-- 🔬 Should test on real data (omit if empty) -->
  <p style="font-size:13px;font-weight:bold;margin-bottom:4px">🔬 Should test on real data</p>
  <ul style="font-size:13px;margin-top:4px">{real_candidates}</ul>

  <!-- ⏳ In progress (omit if none) -->
  <p style="font-size:13px;font-weight:bold;margin-bottom:4px">⏳ In progress</p>
  <ul style="font-size:13px;margin-top:4px">{in_progress}</ul>
```

- [ ] **Step 4: Verify all four section labels are present**

Run: `grep -n "Synthetic benchmarks\|Real data results\|Should test on real data\|In progress\|synthetic_rows\|real_rows\|real_candidates\|in_progress" ~/.claude/skills/weekly-review/SKILL.md`

Expected: all eight terms appear, and the four `{...}` template placeholders are in the HTML block.

- [ ] **Step 5: Commit**

```bash
git add ~/.claude/skills/weekly-review/SKILL.md
git commit -m "feat: weekly-review email — four-section experiment block with synthetic/real categorization"
```
