# research-digest-bot

An AI-powered research workflow for forecasting practitioners. Surfaces relevant ML/TS papers weekly, answers questions about them, and runs end-to-end experiments from arxiv URL to benchmark results — all from Slack and Claude Code.

## What's in here

| Component | What it does |
|---|---|
| **Alfred** (`aws/alfred_*/`) | Slack bot that posts weekly paper digests and answers `@alfred` questions in-thread |
| **Research Brief** (`.claude/skills/research-brief/`) | Curates and posts up to 5 papers each Monday, weighted by your topic preferences and grounded in your active experiment context |
| **Implement Paper** (`.claude/skills/implement-paper/`) | Two-phase CLI skill: interview → plan → implementation → benchmark against synthetic data |
| **Clean Notebook** (`.claude/skills/clean-notebook/`) | Strips bulk/teaching content from Jupyter notebooks |
| **Create Experiment Docs** (`.claude/skills/create-experiment-documentation/`) | Scaffolds a Confluence page for a new experiment |
| **FastAPI server** (`research_digest/`) | Handles Slack webhooks, routes messages to Alfred sessions |

---

## Setup

### 1. Install dependencies

```bash
python3 -m venv venv && source venv/bin/activate
pip install -e .
```

### 2. Environment variables

Copy `.env.example` to `.env` and fill in:

```bash
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
ANTHROPIC_API_KEY=sk-ant-...
GDRIVE_CREDENTIALS_PATH=/path/to/credentials/service-account.json
GDRIVE_ROOT_FOLDER_ID=...
```

### 3. Run locally

```bash
# Start the Slack webhook server
uvicorn research_digest.server:app --reload

# Or test Alfred directly from the CLI
python cli.py <slack_user_id> "Run the research digest."
```

### 4. Deploy to AWS (Lambda)

Requires AWS CLI + SAM and the env vars above exported in your shell:

```bash
cd aws
./deploy.sh        # deploys alfred-bot-2 stack
./deploy_worker.sh # deploys the async worker
```

---

## Claude Skills

Skills live in `.claude/skills/` and are picked up automatically by Claude Code. Install them into your local `~/.claude/skills/` to use them:

```bash
cp -r .claude/skills/* ~/.claude/skills/
```

### `/research-brief`
Generates and posts a weekly digest of up to 5 curated papers to `#research-digest`. Runs automatically every Monday at 8am CT or on-demand. Topic weights are tuned over time based on your feedback.

### `/implement-paper <arxiv-url>`
End-to-end experiment builder in two phases:
- **Phase 1** — interviews you about scope, baseline, and success criterion; writes a plan to your lab notebook
- **Phase 2** (invoke again with same URL) — implements the method, runs cross-validation on 10k synthetic series, writes a README and updates the lab notebook with verdict

Allowed frameworks: `NeuralForecast`, `StatsForecast`, `MLForecast`, `sklearn`.

### `@alfred` (Slack)
Mention `@alfred` in any `#research-digest` thread to ask a question about the paper. Alfred fetches the paper, answers in-thread, and connects it to your active experiments.

---

## Project structure

```
research_digest/        # Core FastAPI app + Alfred session logic
  server.py             # Slack webhook handler
  session.py            # Alfred + digest session runners
  state.py              # GDrive-backed state store
  benchmark/            # Synthetic data generation + metrics (MAE, RMSE, wMAPE, ME)
aws/                    # Lambda handlers + SAM infra
  alfred_webhook/       # Receives Slack events
  alfred_worker/        # Async paper processing worker
  alfred_digest/        # Weekly digest Lambda
  template.yaml         # SAM template
.claude/skills/         # Claude Code skills for the research workflow
tests/                  # pytest suite
```
