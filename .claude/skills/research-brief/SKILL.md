---
name: research-brief
description: Generate and post a weekly research digest of up to 5 curated papers across retail timeseries forecasting, tabular ML, deep learning for TS, and TS analysis. Posts to #research-digest Slack channel with connection prompts grounded in Jack's active experiment context. Runs automatically every Monday 8am CT or on-demand via /research-brief.
---

# Research Brief Skill

## When This Skill Runs
- Automatically every Monday at 8am CT via scheduled cron
- Manually via `/research-brief` in any conversation

## User Context (Baked-In)
Jack Rodenberg, Data Scientist at Daybreak AI. Forecasting retail/supply chain demand.

**Active model stack:**
- LightGBM recursive + direct with power transformations (sqrt, fourth root, log)
- Key finding: pure AR(1) beats Markov regime-switching for retail demand (V11_PureAR)
- Fourth root recursive outperforms sqrt on heavy-tailed distributions; V7 > V5 on Hasbro/SharkNinja
- Ensemble: PowerEnsemble (median > mean), lgb_sq_fourthroot_recursive_V1 is current best single model
- Hierarchical: cross-sectional + temporal reconciliation (MinTraceSparse, TopDownSparse)
- DL experiments tested: DeepMoVE, CycleNet, KAN, TiDE, DLinear, NLinear, NHITS, DeepNPTS, DeepTheta

**Focus areas for curation:** retail demand forecasting, supply chain, tabular ML, deep learning for TS, TS statistical analysis

## State Files
- `~/.claude/skills/research-brief/seen-papers.json` — IDs/URLs of papers already sent
- `~/.claude/skills/research-brief/paper-feedback.json` — topic weights from reactions

---

## Step 0: Scan Vault for Experiment Stats

Before fetching papers, read the experiment lab notebook to build stats for the digest header.

**Path:** `~/ObsidianVault/DaybreakResearch/03-LabNotebook/`

Using Bash (or file reads), list all `.md` files in that directory. Exclude:
- `_template-experiment.md`
- Anything inside subdirectories (`FailureMuseum/`, `CodeSnippets/`, etc.)

For each remaining file, read its frontmatter and extract the `verdict` field. Compute:
- `total_hypotheses`: count of files with a `hypothesis:` field present (any value)
- `successful_experiments`: count of files where `verdict: confirmed` OR `verdict: partial`
- `success_pct`: `round(successful_experiments / total_hypotheses * 100)` (0 if total is 0)

Carry these three values forward for use in Step 7a.

---

## Step 1: Read User State

Call `get_seen_papers` with your user_id to get the list of paper IDs already delivered to this user.
Call `get_user_prefs` with your user_id to get topic keywords and weights.

If either tool returns an error, use these defaults:
- `seen_ids = []`
- `topics = [{"keyword": "retail demand forecasting", "weight": 1.0}, {"keyword": "tabular ML", "weight": 1.0}, {"keyword": "deep learning time series", "weight": 1.0}, {"keyword": "time series statistical analysis", "weight": 1.0}]`

---

## Step 2: Topic Weights

Your topic keywords and weights are pre-loaded from `get_user_prefs`. No Slack reaction reading is needed — weights already reflect your feedback history.

---

## Step 3: Search for Papers (Run All Searches in Parallel)

Use WebSearch and WebFetch to search the past 3 years. Run all queries simultaneously.

Compute `three_years_ago` as today's date minus 3 years in YYYY-MM-DD format, then use it in the `after:` filter below.

**WebSearch queries** (build dynamically from your topics keywords):

For each keyword in `topics` (run all in parallel, weight results by topic weight):
1. `arxiv.org "{keyword}" forecasting after:{three_years_ago}`
2. `arxiv.org "{keyword}" deep learning OR transformer OR foundation model after:{three_years_ago}`

Also run these fixed queries:
- `site:huggingface.co/blog time series forecasting`
- `"time series" forecasting model release open source after:{three_years_ago}`

When scoring, multiply `adjusted_score` by the weight of the closest-matching topic keyword.

**WebFetch:** `https://paperswithcode.com/task/time-series-forecasting` — extract papers listed in the "Latest" or "Recent" section.

For each candidate paper found, extract:
- `title`: full paper title
- `url`: direct link (arxiv abstract page preferred, e.g. `https://arxiv.org/abs/2404.XXXXX`)
- `arxiv_id`: if arxiv, the ID string (e.g., `2404.12345`); otherwise the full URL serves as ID
- `abstract`: 1-2 sentence summary of what it does and what result it achieves
- `tag`: assign ONE from `[Retail]`, `[Tabular ML]`, `[DL-TS]`, `[TS Analysis]` — pick the most specific match
- `has_benchmark`: true if evaluated on M5, ETT, Monash, Electricity, Traffic, Weather, or any M-competition dataset
- `has_code`: true if GitHub link or HuggingFace repo is mentioned

---

## Step 3b: Fetch Credibility Scores (Run in Parallel)

For each candidate paper with an `arxiv_id`, fetch its Semantic Scholar record using WebFetch. Run all fetches in parallel.

URL pattern: `https://api.semanticscholar.org/graph/v1/paper/arXiv:{arxiv_id}?fields=citationCount,authors.hIndex,authors.citationCount`

If a paper returns 404, times out, or has missing fields, treat as neutral — all values default to 0. Do not discard the paper.

Extract per paper:
- `citation_count`: integer from `citationCount` (default 0)
- `max_h_index`: max of all authors' `hIndex` values (default 0 if absent)

---

## Step 4: Filter and Score

**Dedup:** For each candidate, check if `arxiv_id` or `url` is in `seen_ids`. If yes, discard.

**Score each remaining paper:**

```
# Content score
base_score = 0
if has_benchmark: base_score += 1
if tag == "[Retail]" or abstract mentions retail/demand/supply chain: base_score += 1
if novel mechanism (not "we apply X to Y", not dataset-only, not pure theory): base_score += 1
if pure theory (no experiments) OR (no code AND no benchmark): base_score -= 1

# Author credibility (primary signal)
if max_h_index >= 30:   author_score = 1.5
elif max_h_index >= 15: author_score = 1.0
elif max_h_index >= 5:  author_score = 0.5
else:                   author_score = 0.0

# Paper citation count (secondary boost)
if citation_count >= 50:   cite_score = 0.5
elif citation_count >= 10: cite_score = 0.3
else:                      cite_score = 0.0

base_score = base_score + author_score + cite_score
adjusted_score = base_score * topic_weights[tag]
```

**Threshold:** Keep only papers with `adjusted_score >= 2.0`.

**Quality caveats** — flag each paper that applies:
- `no_code`: has_code is false
- `non_standard_benchmark`: benchmark dataset not in the standard list above
- `preprint_only`: arxiv only, no venue acceptance

---

## Step 5: Select Top Picks

Sort qualifying papers by `adjusted_score` descending. Take up to 5.

If 0 qualifying papers: skip to Error Handling.
If 1–4 qualifying papers: proceed with however many qualified; note the count in the digest footer.

---

## Step 6: Generate Connection Prompts

For each selected paper, check for connections to Jack's active work. Look specifically for:

- **Power transformations:** Any paper about target encoding, Box-Cox, sqrt/log/fourth-root transforms, or output variance stabilization → connect to V1-V7 experiment findings
- **AR(1) / autocorrelation:** Papers about temporal dependencies, lag features, or autoregressive components → connect to V11_PureAR finding
- **Regime switching / change detection:** Papers on structural breaks, level shifts, Markov models → connect to why V11_PureAR beat MarkovianTheta
- **Hierarchical forecasting:** Reconciliation, bottom-up, top-down, MinTrace → connect to HierarchicalMLForecast work
- **Heavy-tailed demand:** Intermittent demand, Croston, sparse series → connect to fourth root outperforming sqrt
- **Any DL architecture Jack tested:** If paper proposes variant of DeepMoVE/CycleNet/KAN/TiDE/DLinear/NLinear/NHITS → compare directly to Jack's benchmark results
- **Foundation models for TS:** Chronos, TimeGPT, Lag-Llama, Moirai → connect to cold-start handling in MarkovianTheta

If a genuine connection exists: write one sentence starting with `→ `
If no clear connection: omit the line entirely. Never force relevance.

---

## Step 7: Format and Post to Slack

**7a. Post parent message to channel `C0AT9D2UYUX`:**

```
📡 *Weekly Research Digest* — [Month DD, YYYY]
_[N] pick[s] across retail forecasting, tabular ML, DL-TS, and TS analysis_
_🧪 [total_hypotheses] hypotheses tested · ✅ [successful_experiments] successful ([success_pct]%)_
```

Save the `ts` value returned — needed for threading all paper replies.

**7b. For each paper (1 to N), post as a thread reply using `thread_ts`:**

```
*[number]. [Paper Title](url)* `[TAG]`
[Sentence 1: what it does.] [Sentence 2: what result it achieves / why it matters.]
→ _[Connection prompt — only if genuine]_
[⚠️ No public code yet.] ← only if no_code caveat applies
[⚠️ Non-standard benchmark.] ← only if non_standard_benchmark applies
```

**7c. Write papers back to vault (run after posting, before footer)**

For each paper that generated a genuine connection prompt (`→` line), find the most relevant open experiment file and attach the paper URL.

1. Extract the connection topic from the `→` sentence (e.g., "zero-inflated loss", "AR(1)", "hierarchical reconciliation").
2. List all `.md` files in `~/ObsidianVault/DaybreakResearch/03-LabNotebook/` (excluding template and subdirs). For each, read the `hypothesis:` frontmatter field.
3. Find the best keyword match between the connection topic and the hypothesis text. If a match is found and the file has a `## Links` section with a `- Papers:` line, append the paper URL (in markdown link format `[Title](url)`) to that line.
   - If the `- Papers:` line is empty: replace it with `- Papers: [Title](url)`
   - If it already has content: append `, [Title](url)`
4. If no matching experiment file is found, skip silently — do not create a new file.

**7d. Post footer as the final thread reply:**

```
---
_Sources: arxiv cs.LG · Papers with Code · HuggingFace_
_React 👍 or 👎 on each paper above to tune future picks_
_Lighter week — only [N] papers cleared the quality bar._ ← only include this line if N < 5
_To adjust topics or cadence: update ~/.claude/skills/research-brief/SKILL.md_
```

---

## Step 8: Save State and Collect Feedback

Call `save_seen_papers` with your user_id and the list of all paper IDs delivered this run.

Then send this message to the user in the current chat:
"React 👍/👎 on each paper in Slack, or tell me here if you'd like to adjust your topics — add keywords, remove ones that aren't useful, or reweight them."

If the user provides feedback in this session, update the topics list and call `save_user_prefs` with the full updated `[{"keyword": "...", "weight": N}]` array.

---

## Error Handling

If all searches fail or 0 papers pass the quality filter, post to channel `C0AT9D2UYUX`:

```
⚠️ *Research Digest — [Date]*
_Agent encountered errors or found no qualifying papers this week._
_Check skill logs or run `/research-brief` manually to retry._
```

Never silently skip a scheduled run.
