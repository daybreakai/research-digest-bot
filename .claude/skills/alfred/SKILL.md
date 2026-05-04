---
name: alfred
description: Use when polling #research-digest for unanswered @alfred thread replies and answering questions about papers in the weekly digest
---

# Alfred: Conversational Paper Assistant

## Overview

Alfred polls `#research-digest` for thread replies containing `@alfred`, fetches the referenced paper, answers the question, and posts a reply in-thread. Runs on a 15-minute cron cycle.

## State

- File: `~/.claude/skills/alfred/alfred-answered.json`
- Format: `{"answered_ts": ["ts1", "ts2", ...]}`
- Tracks the Slack `ts` of every `@alfred` message already answered — prevents duplicate replies across poll cycles

## Core Flow

### Step 1: Load State
Read `~/.claude/skills/alfred/alfred-answered.json`. Extract `answered_ts`. Default to `[]` if missing or malformed.

### Step 1b: Load Live Vault Context

Run both reads in parallel:

**Active briefing** — read `~/ObsidianVault/DaybreakResearch/05-ClaudeContext/active-briefing.md`. Extract the full text. This replaces the baked-in context block — use whatever is in the file as the source of truth for Jack's current work and focus areas. If the file is missing, fall back to the static context at the bottom of this skill.

**Open hypotheses** — list all `.md` files in `~/ObsidianVault/DaybreakResearch/03-LabNotebook/` (excluding `_template-experiment.md` and subdirs). For each file, read the frontmatter and extract `hypothesis:` and `verdict:`. Keep only files where `verdict: null` or `verdict` is absent. Build a list:

```
open_hypotheses = [
  { file: "2026-04-27-zeroinflated-lgbm-loss-sparse.md", hypothesis: "..." },
  ...
]
```

Carry `active_briefing_text` and `open_hypotheses` forward — they are used in Step 4d and 4f.

### Step 2: Poll Channel
Read `#research-digest` (channel `C0AT9D2UYUX`, last 20 messages). Identify all parent digest messages — those whose text contains "Weekly Research Digest".

### Step 3: Find Unanswered @alfred Messages
For each digest parent, read its full thread. Collect replies where:
- Text contains `@alfred`
- `ts` NOT in `answered_ts`

If none found across all threads: **exit silently**.

### Step 4: Process Each Unanswered Message

**4a. Identify the paper**
Check for a URL in this order — use the first source that yields one:
1. **The `@alfred` message itself** — scan for any URL (arxiv, huggingface, semantic scholar, doi, etc.)
2. **The thread parent** — extract the paper title and URL from the research-brief format

If neither yields a URL, post the "couldn't find the paper link" edge case response and skip to 4g.

**4b. Parse the question**
Extract everything after `@alfred` that is not a URL. Treat as free-form natural language.
If nothing remains (message was just a URL, or URL + no other text), default the question to: **"Summarize this paper."**

**4c. Fetch the paper**
- Primary: `WebFetch` the arxiv abstract page (title, abstract, authors, date)
- If question requires methodology or results depth: fetch the full PDF or HTML paper page

**4d. Generate response**
Answer directly and concisely. Check for genuine connections to Jack's active work using `active_briefing_text` (loaded in Step 1b) as the primary context. Then check `open_hypotheses` — if the paper is directly relevant to any open hypothesis, name it explicitly in the connection line. If a genuine connection exists, append it as `→ _[connection]_`. **Never force relevance — omit entirely if no genuine connection.**

Connection priority:
1. **Open hypothesis match** (strongest): paper bears directly on a currently running experiment → name the hypothesis file, e.g. `→ _Directly relevant to your open experiment on zero-inflated loss variants — [[2026-04-27-zeroinflated-lgbm-loss-sparse]]_`
2. **Active briefing match**: paper connects to something in `active_briefing_text` but no specific open experiment → describe the connection in one sentence
3. No genuine match → omit the `→` line entirely

**4e. Post reply**
Use `slack_send_message` with `thread_ts` set to the digest parent message's `ts`:

```
*Alfred* 🤖
[Answer to question]
→ _[Connection to your work — only if genuine]_
```

**4f. Write paper to vault (only if genuine connection found)**

If step 4d produced a genuine `→ _[connection]_` line, attach the paper to the relevant experiment file:

1. Extract the connection topic from the `→` sentence.
2. List all `.md` files in `~/ObsidianVault/DaybreakResearch/03-LabNotebook/` (excluding `_template-experiment.md` and subdirs). For each, read the `hypothesis:` frontmatter field.
3. Find the best keyword match between the connection topic and the hypothesis text. If a match is found and the file has a `- Papers:` line under `## Links`:
   - If the line is empty: replace it with `- Papers: [Title](url)`
   - If it already has content: append `, [Title](url)`
4. If no match is found, skip silently.

**4g. Mark as answered**
Append the `@alfred` message's `ts` to `answered_ts`. Write updated `alfred-answered.json`.

**4h. Write to paper cache**

Append to `~/.claude/skills/alfred/paper-cache.json`:

```json
{
  "url": "<paper url from step 4a>",
  "title": "<paper title>",
  "summary": "<Alfred's answer body from step 4e, excluding the → connection line, truncated to first 200 words>",
  "methods_summary": "<1–2 sentences on the core method, extracted from the paper content fetched in step 4c>",
  "connections": ["<the → connection text generated in step 4d, without the → symbol and markdown italics; empty array if no connection was generated>"]
}
```

If `paper-cache.json` does not exist, create it as an empty JSON array `[]` first. If the URL already exists in the cache, skip — do not overwrite (idempotent).

## Edge Cases

| Situation | Alfred's response |
|-----------|-------------------|
| No question after `@alfred` (URL only or empty) | Default to summarizing the paper — do not ask for clarification |
| URL in `@alfred` message | Use it directly — do not require the paper to be from the digest |
| No URL anywhere (message nor thread parent) | `*Alfred* 🤖 I couldn't find the paper link. Can you paste the arxiv URL?` |
| WebFetch fails | `*Alfred* 🤖 I had trouble fetching this paper. Try again or paste a direct arxiv link.` |
| Multiple `@alfred` in same thread | Process all, post replies in order |

## Scope

Alfred only responds to threads under "Weekly Research Digest" parent messages in `#research-digest`. Does not handle DMs, other channels, or non-digest threads.

---

## Fallback Context (use only if active-briefing.md is unreachable)

- Power transforms (sqrt, fourth root, log, Box-Cox) → V1-V7 experiments
- AR(1), lag features, autoregressive components → V11_PureAR finding
- Regime switching, structural breaks, Markov models → why V11_PureAR beat MarkovianTheta
- Hierarchical reconciliation, MinTrace, TopDown → HierarchicalMLForecast work
- Heavy-tailed / intermittent demand, Croston → fourth root outperforming sqrt
- DeepMoVE, CycleNet, KAN, TiDE, DLinear, NLinear, NHITS → DL benchmark results
- Foundation models (Chronos, TimeGPT, Lag-Llama, Moirai) → cold-start handling in MarkovianTheta
