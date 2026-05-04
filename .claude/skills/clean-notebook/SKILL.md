---
name: clean-notebook
description: Use when asked to clean up, declutter, remove bulk, or strip teaching content from Jupyter notebooks - removes emojis, verbose markdown, decorative formatting while preserving all technical content
---

# Clean Notebook

## Overview

Transform teaching-style Jupyter notebooks into clean, production-ready reference material. Removes ~60-70% of bulk (verbose markdown, emojis, decorative separators, diagnostic blocks) while preserving 100% of technical content (data contracts, configuration, executable code).

**Core principle:** Technical content lives. Pedagogical scaffolding goes.

## When to Use

**Triggering symptoms:**
- Teaching-style notebooks with emojis (✓, ✗, 📊, 📈, ⚠️)
- Decorative separators (`"=" * 70`, `"=" * 80`)
- Diagnostic print blocks (environment checks, verbose status)
- Verbose markdown explaining "why" (philosophical context, learning objectives)
- Comments with exclamation marks or motivational language
- Section headers like "What's in this notebook", "Key Concept:", "Let's..."

Use when: User asks to "clean up", "declutter", "remove bulk", "strip teaching content", or "make it production-ready"

**Do NOT use when:**
- Notebook is already clean (minimal prose, no decorative formatting)
- User wants to preserve teaching content (pedagogical value is priority)
- Removing content would break notebook structure or execution

## Advanced Features

### Import Organization

Automatically consolidate and categorize all imports into a single organized cell at notebook start:

**Categories (in order):**
1. **Standard Library**: `sys`, `os`, `json`, `re`, `pathlib`, `typing`, etc.
2. **Third-Party**: `pandas`, `numpy`, `matplotlib`, `torch`, `sklearn`, etc.
3. **Local Imports**: `from src import`, project-specific imports

**Process:**
- Scans all code cells for import statements
- Deduplicates (removes repeated imports)
- Creates new organized cell at position 0 (or after cell 0 if markdown exists)
- Removes duplicate imports from original cells
- Maintains any `__future__` imports at the very top

**Example:**

```python
# ✗ BEFORE: Imports scattered across cells
# Cell 2
import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from src.metrics import MetricsCalculator

# Cell 8
import numpy as np
from typing import Optional

# ✓ AFTER: Organized import cell at top
# Cell 1 (new)
import sys
import json
import warnings
from pathlib import Path
from typing import Optional, Tuple, List, Dict

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go

from src import CacheManager, ArtifactManager
from src.metrics import MetricsCalculator, MetricResults
```

### Comment-to-Markdown Transfer

Extract verbose code comments and promote them to markdown cells for better documentation:

**Criteria for extraction:**
- Inline comments with 40+ characters
- Block comments (3+ lines explaining logic)
- Comments describing business logic or data contracts
- NOT extracted: brief single-line comments (<40 chars)

**Process:**
- Identifies verbose comments in code cells
- Creates markdown section headers for related comments
- Moves explanatory comments to markdown above code cells
- Leaves brief functional comments in-place
- Notes which comments were moved

**Example:**

```python
# ✗ BEFORE: Comment buried in code
# Step 1: Compute short-horizon metrics (weeks 1-4 at store level - used for daily decisions)
# Step 2: Compute long-horizon metrics (weeks 5-13 at SKU level - used for replenishment)
short_results = calculator.compute_metrics(df, error_level=["unique_id","ds"])

# ✓ AFTER: Comment in markdown, clean code
# Markdown cell (new):
## Metric Computation Strategy

Compute metrics at two decision grains:
- **Short-horizon (weeks 1-4)**: Store-level metrics for daily operational decisions
- **Long-horizon (weeks 5-13)**: SKU-level metrics for replenishment planning

# Code cell:
short_results = calculator.compute_metrics(df, error_level=["unique_id","ds"])
```

## Removal Rules

### Markdown Cell Removal

**Strip completely:**
- Pure philosophical/motivational paragraphs ("Why this matters...", "Rule of thumb:", "Let's explore...")
- Decorative visual separators (lines of `=`, `-`, `*`)
- Emojis and Unicode symbols (✓, ✗, 📊, 📈, ⚠️, 🔄, ⏳, 💡, 🎯, 🚀, etc.)
- HTML styling tags (`<div style="...">`, `<span style="...">`)
- Repetitive context that duplicates code comments

**Clean (simplify, don't remove):**
- Teaching headers → Keep as section headers only
  - ✗ "## What's in this notebook" + 5-line intro → ✓ "## Setup"
  - ✗ "## Why this matters" + explanation → ✓ (Remove entirely)
  - ✓ "## Section 3: Compute Metrics" → Keep (section structure)

### Code Cell Removal

**Strip:**
- Diagnostic print blocks (environment checks, verbose status displays)
- Comments with emojis or exclamation marks ("✓ Setup complete!", "🔍 Investigating...")
- ASCII art headers and decorative prints (`print("=" * 70)`)
- Verbose status messages ("DIAGNOSTIC: Python Environment Setup")

**Keep:**
- Brief functional comments (single-line, explains what code does)
- Data contract definitions (`ID_COL = "unique_id"`)
- Configuration constants (SHORT_HORIZON, LONG_HORIZON)
- Critical warnings about execution order
- All executable code (unchanged)

### Markdown Content Examples

```markdown
# ✗ REMOVE: Teaching prose

## What's in this notebook
- Compute executive metrics at business decision grains
- Build three scoreboard views
- Apply the Anchor Gate → Rank → Veto selection logic

## Key Concept: The Scoreboard Recipe
1. Start with raw CV output
2. Decide the decision grain
3. Aggregate forecasts and actuals FIRST
[10 more lines of pedagogical explanation]

**Order matters. This is non-negotiable.**

---

# ✓ KEEP: Technical documentation

## Setup
Data contract: ID_COL, TIME_COL, TARGET_COL, CUTOFF_COL

## Compute Metrics
Order matters: aggregate forecasts/actuals FIRST, then compute error.
```

### Code Examples

```python
# ✗ REMOVE: Diagnostic block
print("=" * 70)
print("DIAGNOSTIC: Python Environment Setup")
print("=" * 70)
print(f"\n1. Python Interpreter:")
print(f"   sys.executable: {sys.executable}")
is_venv = ".venv" in sys.executable
print(f"   Using Poetry venv: {is_venv} {'✓' if is_venv else '✗ WARNING!'}")
print(f"\n2. Current Working Directory:")
# ... 30 more lines of environment printing

# ✓ KEEP: Minimal setup
sys.path.insert(0, str(PROJECT_ROOT))
from src import CacheManager, ArtifactManager

# ✓ KEEP: Functional comments
ID_COL = "unique_id"          # Data contract: unique identifier
TIME_COL = "ds"               # Data contract: date stamp
TARGET_COL = "y"              # Data contract: actual values
CUTOFF_COL = "cutoff"         # Data contract: backtest cutoff date

# ✗ REMOVE: Comment with emoji
print("✓ Setup complete!")

# ✓ KEEP: Informative comment
# Compute metrics at segment level directly
segment_results = calculator.compute_metrics(...)

# ✗ REMOVE: Verbose decorative separator
print("=" * 60)
print("SEGMENT ANALYSIS")
print("=" * 60)

# ✓ KEEP: Minimal separator and message if critical
print("\nSegment Analysis:")
```

## Preservation Rules

**Always keep:**
- Section hierarchy (## Main, ### Sub)
- Data contracts (`ID_COL = "..."`, configuration tables)
- Technical constraints and warnings
- All executable code (cell execution logic)
- Variable assignments and imports
- Function/class definitions
- Brief functional comments

**Examples of what preserves:**

```python
# ✓ KEEP: Data contract
ID_COL = "unique_id"
TIME_COL = "ds"
TARGET_COL = "y"
data_contract_cols = [ID_COL, TIME_COL, TARGET_COL]

# ✓ KEEP: Configuration
SHORT_HORIZON = (1, 4)     # Weeks 1-4
LONG_HORIZON = (5, 13)     # Weeks 5-13
ANCHOR_MODEL = "SN52"

# ✓ KEEP: Critical warning (brief)
# Order matters: aggregate forecasts/actuals FIRST, then compute error
metric_level = calculator.compute_metrics(...)

# ✓ KEEP: Section headers
## Section 1: Setup & Imports
## Section 2: Load Data
```

## Process Flow

**1. User invokes skill** with optional flags:
   - `--clean`: Remove teaching content (default: enabled)
   - `--organize-imports`: Consolidate imports (default: disabled)
   - `--move-comments`: Extract verbose comments to markdown (default: disabled)
   - `--all`: Apply all transformations (default: disabled)

**2. Read notebook** - Parse JSON structure

**3. Create `.backup` file** - Safety first (e.g., `notebook.ipynb.backup`)

**4. Analyze content** - Collect all proposed changes:
   - Which cells will be deleted entirely
   - Which cells will be stripped/simplified
   - What content will be removed from each cell

**5. Show preview/diff** - Display what will change:
   ```
   PREVIEW: Changes to be applied
   ═════════════════════════════════════════════════════════════════

   CELLS TO DELETE (2 total):
   - Cell 0: (markdown) "## What's in this notebook" (5 lines)
     Reason: Pure teaching prose, no technical content

   - Cell 1: (code) "DIAGNOSTIC: Python Environment Setup" (40 lines)
     Reason: Diagnostic print block, not needed for execution

   CELLS TO SIMPLIFY (8 total):

   - Cell 3: (code) "print('✓ Setup complete')" (1 line → DELETE)
     Before: print('✓ Setup complete!')
     After: [removed - not functional output]

   - Cell 7: (markdown) "## Section 5..."
     Before: (5 lines with emojis and teaching context)
     After: ## Section 5: Visualization

   STATISTICS:
   - Cells deleted: 2
   - Cells simplified: 8
   - Lines removed: 127
   - File size: 8.2 KB → 5.1 KB (38% reduction)
   ```

**6. Wait for user approval** - Checkpoint before destructive operation

**7. Apply changes if approved** - Backup exists, safe to proceed:
   - Delete identified cells
   - Strip content from identified cells
   - Update notebook structure
   - Validate JSON

**8. Save cleaned notebook** - Same path, original backed up

**9. Report statistics:**
   ```
   ✓ Cleaned notebook saved
   - Cells deleted: 2
   - Cells modified: 8
   - Lines removed: 127
   - Original size: 8.2 KB
   - New size: 5.1 KB (38% reduction)
   - Backup: notebook.ipynb.backup
   ```

## Common Mistakes

**What NOT to remove:**

| Item | Why Keep | Example |
|------|----------|---------|
| Section headers | Maintains structure | `## Setup`, `## Analysis` |
| Data contracts | Critical for execution | `ID_COL = "unique_id"` |
| Configuration | Readers need these | `SHORT_HORIZON = (1, 4)` |
| Functional comments | Explain non-obvious code | `# Aggregate by segment first` |
| All code | Execution logic | Even if verbose, code runs |
| Brief warnings | Critical context | `# Order matters: aggregate FIRST` |
| Variable assignments | Data flow | `df['dept_id'] = df['unique_id'].str.split(...)` |
| Imports and setup | Notebook needs these | `from src import CacheManager` |

**What ALWAYS removes:**

| Item | Why Remove | Example |
|------|-----------|---------|
| Emojis | Bulk without meaning | `✓ ✗ 📊 📈 ⚠️` |
| Decorative separators | Pure formatting | `print("=" * 70)` |
| "What's in this notebook" | Teaching scaffolding | Section 0 intro paragraphs |
| Diagnostic print blocks | Environment checks | 40-line setup diagnostics |
| Motivational language | Teaching, not content | "Why this matters:", "Let's explore..." |
| Comments with emojis | Verbose status | `# ✓ Setup complete!` |
| Philosophies | Pedagogical | "Order matters. This is non-negotiable." |

## Red Flags - STOP and Reconsider

These situations mean you should skip cleanup or ask clarification:

- Notebook used FOR teaching (preserve teaching content)
- User hesitant about removing content (offer selective cleanup instead)
- Unclear what is "teaching" vs "technical" (ask user to clarify specific sections)
- Notebook has critical inline documentation (evaluate before removing)
- Removing content breaks notebook execution (NEVER do this)

## Quality Checks (After Applying Changes)

Verify cleaned notebook:
- [ ] All data contracts present (ID_COL, TIME_COL, etc.)
- [ ] All section headers maintained (## Section 1, ## Section 2)
- [ ] No emojis remain anywhere
- [ ] Comments are brief and functional
- [ ] Code executes cell-by-cell (if applicable)
- [ ] Variable definitions unchanged
- [ ] Backup file created and accessible
- [ ] JSON structure is valid
- [ ] Line count reduced by ~60-70%

## Before/After Example

**BEFORE (Teaching Style):**
```python
# Cell 0 (markdown)
# === Diagnostic: Python Environment Setup ===
# ✓ Using Poetry venv
# ✗ sys.path includes PROJECT_ROOT
# 📊 Attempting to import src module...

# Cell 1 (code)
print("=" * 70)
print("DIAGNOSTIC: Python Environment Setup")
print("=" * 70)
print(f"\n1. Python Interpreter:")
print(f"   sys.executable: {sys.executable}")
is_venv = ".venv" in sys.executable
print(f"   Using Poetry venv: {is_venv} {'✓' if is_venv else '✗ WARNING!'}")
# ... 30 more lines of diagnostic printing
print("✓ Setup complete!")

# Cell 2 (markdown)
## Key Concept: Understanding the Setup
When working with Jupyter, the environment is critical. Here's why...
[5 paragraphs on why environment matters]

# Cell 3 (code)
ID_COL = "unique_id"  # ✓ Column for unique identifiers
TIME_COL = "ds"       # ✓ Column for timestamps
```

**AFTER (Clean Reference):**
```python
# Cell 0 (code)
sys.path.insert(0, str(PROJECT_ROOT))
from src import CacheManager, ArtifactManager

# Cell 1 (code)
ID_COL = "unique_id"     # Data contract: unique identifier
TIME_COL = "ds"          # Data contract: timestamp
TARGET_COL = "y"         # Data contract: actual values
CUTOFF_COL = "cutoff"    # Data contract: backtest cutoff
```

**Impact:**
- Before: 70+ lines, 3 cells, 40% diagnostic/pedagogical content
- After: 12 lines, 2 cells, 100% technical content
- Reduction: ~80%

## Implementation

This skill guides manual cleanup. For automated implementation:

1. **Parse notebook JSON** - Read cell structure
2. **Apply rules** - Identify cells/content to remove using patterns from this skill
3. **Generate diff** - Show user what will change before applying
4. **Create backup** - `notebook.ipynb.backup`
5. **Apply changes** - Remove/strip identified content
6. **Validate** - Verify notebook is still valid JSON
7. **Report** - Show statistics on cleanup

See supporting tool `clean_notebook_tool.py` for implementation.
