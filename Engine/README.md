# Paladin Engine

The security engine powering Paladin — an AI agent security layer that intercepts, evaluates, and gates every tool-use command before it executes.

---

## What it does

Every command an AI agent attempts passes through three evaluation stages:

```
Agent command
     │
     ▼
┌─────────────────┐
│  Context Engine │  WHO? WHAT? WHERE? — enriches raw action into structured context
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Intent Analyzer│  WHY? — deterministic rules + optional AI analysis
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Risk Engine    │  HOW DANGEROUS? — SentenceTransformer cosine similarity
└────────┬────────┘
         │
     ┌───┴───┐
     │       │
   SAFE    HIGH RISK
     │       │
  continue  ┌┴──────────────┐
            │  flagger.py   │  Permission gate — user approves or denies
            └───────────────┘
```

---

## Project structure

```
Engine/
├── kiro_guard.py          Wraps kiro-cli; intercepts every tool call pre-execution
├── watcher.py             File watcher; processes prompts from trialHack_output.csv
├── flagger.py             Terminal permission gate (renders warning cards, ask y/n)
├── Backend.py             Forwards clean prompts to kiro-cli
│
├── Risk_Engine/
│   ├── RiskEngine.py      Cosine similarity scorer (SentenceTransformer)
│   └── Tier2_Plotting.py  Risk visualization helpers
│
├── Context_Engine/
│   ├── requirements.txt
│   ├── trialHack.py       CLI test harness for the context pipeline
│   └── paladin/
│       ├── schemas/
│       │   ├── action.py      AgentAction  — input model (Pydantic)
│       │   ├── context.py     ContextResult — output of Context Engine
│       │   └── intent.py      IntentResult  — output of Intent Analyzer
│       │
│       ├── context/
│       │   ├── engine.py      ContextEngine class (main entry point)
│       │   ├── analyzer.py    Builds ActionContext from AgentAction
│       │   ├── classifiers.py File / command classification functions
│       │   ├── classifier.py  Target classification (sensitivity, category)
│       │   ├── history.py     ActionHistory ring buffer
│       │   ├── models.py      ActionContext Pydantic model
│       │   └── patterns.py    Compiled regex / path patterns
│       │
│       ├── intent/
│       │   ├── analyzer.py    IntentAnalyzer — hybrid deterministic + AI
│       │   ├── rules.py       Priority-ordered deterministic intent rules
│       │   └── service.py     AIIntentAnalyzer interface + HTTP/Stub implementations
│       │
│       └── tests/
│           ├── test_context.py         50+ unit tests for Context Engine
│           ├── test_context_engine.py  Integration tests for ContextEngine
│           └── test_intent.py          Intent Analyzer unit + integration tests
│
└── assets/
    ├── embedded_mal_prompts.npy        Pre-embedded malicious prompt vectors
    └── malicious_prompts_data_plus_500.csv  Raw malicious prompt dataset
```

---

## Components

### kiro_guard.py

Wraps `kiro-cli` and intercepts every tool-use event before execution.

- Spawns `kiro-cli` with `--output-format stream-json`
- Parses `tool_call` events from stdout in a background thread
- Runs `risk_score()` on every command string
- **SAFE** (< 0.5): green badge, kiro continues
- **WARN** (0.5–0.7): orange badge, kiro continues
- **HIGH** (≥ 0.7): kills kiro immediately, shows permission gate via `flagger.py`
  - User approves → restarts kiro with the same prompt
  - User denies → blocked card, paladin idles

```python
from Engine.kiro_guard import run_guarded
run_guarded(prompt, push_fn=_push, render_line_fn=_render_line)
```

Direct CLI test:
```bash
python Engine/kiro_guard.py "list the files in this directory"
```

### Risk Engine (`Risk_Engine/RiskEngine.py`)

Scores any prompt against a library of known malicious prompts using semantic similarity.

- Model: `all-MiniLM-L6-v2` (SentenceTransformer, loaded once at startup)
- Embeddings: `assets/embedded_mal_prompts.npy` (~500 pre-embedded vectors)
- Metric: cosine similarity — max score across all malicious reference prompts

```python
from Risk_Engine.RiskEngine import risk_score

risk_factor, score_str = risk_score("delete all files in /etc")
# risk_factor: float (cosine similarity, -1 to 1)
# score_str:   human-readable score string
```

Thresholds:

| Score | Tier | Action |
|-------|------|--------|
| < 0.5 | Safe | Forward to kiro |
| 0.5 – 0.7 | Warn | Forward with warning badge |
| ≥ 0.7 | High risk | Block and show permission gate |

### Context Engine (`Context_Engine/paladin/context/`)

Enriches a raw `AgentAction` into a fully-normalized `ActionContext` that all downstream engines consume. Does not make allow/deny decisions.

Answers six questions about every action:

| Question | Field |
|----------|-------|
| WHO? | Agent identity |
| WHAT? | Action type and target |
| WHERE? | Working directory, OS, shell, project root |
| TARGET? | Resource type, category, sensitivity |
| HISTORY? | Recent agent actions (ring buffer) |
| OUTSIDE PROJECT? | Is the target outside the project root? |

```python
from paladin.context.engine import ContextEngine
from paladin.schemas.action import AgentAction

engine = ContextEngine()
context = engine.build_context(action)
```

### Intent Analyzer (`Context_Engine/paladin/intent/`)

Classifies the intent behind an agent action. Uses a hybrid approach:

1. **Deterministic rules** (`rules.py`) — priority-ordered pattern matching, high confidence, no latency
2. **AI analysis** (`service.py`) — HTTP call to an AI service, used when deterministic confidence is low

If deterministic confidence is high enough, AI is skipped entirely.

Intent categories: `install_dependency`, `delete_resource`, `access_credentials`, `access_sensitive_configuration`, `access_configuration`, `modify_project_file`, `read_project_file`, `execute_command`, `network_access`, `spawn_process`, `modify_system`, `unknown`

### flagger.py

Terminal permission gate rendered when a high-risk command is intercepted.

- Renders a styled warning card with the blocked command
- Prompts for explicit `y / n` approval
- Approve → forwards prompt to kiro-cli via paladin's renderer
- Deny → renders a blocked card and exits cleanly

### watcher.py

File-based trigger for the pipeline. Watches `Context_Engine/trialHack_output.csv` for new rows and processes each prompt through the Risk Engine in-process (SentenceTransformer loads once at startup).

---

## Setup

### Requirements

```bash
# Python 3.11+
pip install sentence-transformers numpy pandas pydantic
```

Full requirements are in `Context_Engine/requirements.txt`.

### kiro-cli

`kiro_guard.py` requires `kiro-cli` to be installed and logged in:

```bash
# Install from https://kiro.ai
kiro login
```

---

## Running tests

```bash
cd Engine/Context_Engine
python -m pytest paladin/tests/ -v
```

Tests cover:
- Context Engine classification (file sensitivity, SSH keys, cloud credentials, shell history, system paths)
- ActionHistory ring buffer behavior
- IntentAnalyzer deterministic rules, AI fallback, confidence merging
- Full pipeline integration tests

---

## Risk score internals

```
user prompt
    │
    ▼ model.encode(prompt, normalize_embeddings=True)
unit vector (384 dims)
    │
    ▼ np.dot(MAL_PROMPTS, u_vector)   # MAL_PROMPTS shape: (N, 384)
cosine similarities against all N malicious reference prompts
    │
    ▼ max(similarities)
risk_factor  →  thresholded into SAFE / WARN / HIGH
```

Negative cosine values are handled via `log(|value|) * 10` to keep the score meaningful across the full range.
