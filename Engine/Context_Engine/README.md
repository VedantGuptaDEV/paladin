# Paladin — Context and Intent Analysis Engine

A standalone Python module that analyses AI agent actions and returns structured
context and intent information for consumption by the Policy Engine, Risk Engine,
and Decision Engine.

## Pipeline position

```
Agent Action
  → Context Engine        ← this module
  → Intent Analyzer       ← this module
  → Policy Engine
  → Risk Engine
  → Decision Engine
  → ALLOW / DENY / REQUIRE_APPROVAL
```

## Project structure

```
paladin-engine/
├── paladin/
│   ├── schemas/
│   │   ├── action.py       AgentAction  — input model
│   │   ├── context.py      ContextResult — output of Context Engine
│   │   └── intent.py       IntentResult  — output of Intent Analyzer
│   │
│   ├── context/
│   │   ├── patterns.py     Regex/path patterns (compiled at import time)
│   │   ├── classifiers.py  Pure classification functions
│   │   └── analyzer.py     ContextEngine class
│   │
│   ├── intent/
│   │   ├── rules.py        Deterministic intent rules (priority-ordered)
│   │   ├── service.py      AIIntentAnalyzer interface + StubAIAnalyzer + HttpAIAnalyzer scaffold
│   │   └── analyzer.py     IntentAnalyzer hybrid class
│   │
│   └── tests/
│       ├── test_context.py 50+ unit tests for Context Engine
│       └── test_intent.py  Unit + integration tests for Intent Analyzer
│
├── requirements.txt
└── README.md
```

## Installation

```bash
cd paladin-engine
pip install -r requirements.txt
```

## Quick start

```python
from paladin.schemas.action import AgentAction
from paladin.context.analyzer import ContextEngine
from paladin.intent.analyzer import IntentAnalyzer

# Instantiate once — both are stateless and thread-safe
context_engine = ContextEngine()
intent_analyzer = IntentAnalyzer()

# Build an action
action = AgentAction(
    action_id="req-001",
    agent="kiro",
    action_type="file_read",
    target="/home/user/.ssh/config",
    command=None,
    task_context="Configuring the development environment",
    metadata={},
)

# Analyse context (synchronous, deterministic)
context = context_engine.analyze(action)
print(context.resource_type)         # ssh_configuration
print(context.sensitivity)           # HIGH
print(context.contains_credentials)  # False
print(context.requires_special_attention)  # True

# Analyse intent (synchronous, deterministic-only)
intent = intent_analyzer.analyze_sync(action, context)
print(intent.intent)      # access_sensitive_configuration
print(intent.confidence)  # 0.9
print(intent.reason)      # "The agent is attempting to access an SSH resource..."

# Serialise to dict (for Policy/Risk/Decision engines)
context_dict = context.model_dump()
intent_dict  = intent.model_dump()
```

## Async usage (with AI service)

```python
import asyncio
from paladin.intent.service import HttpAIAnalyzer
from paladin.intent.analyzer import IntentAnalyzer

ai_service = HttpAIAnalyzer(
    base_url="http://localhost:9000",   # Person 2's AI service
    api_key="your-api-key",
    timeout=2.0,
)
analyzer = IntentAnalyzer(ai_service=ai_service)

async def evaluate(action):
    context = context_engine.analyze(action)
    intent  = await analyzer.analyze(action, context)
    return context, intent

context, intent = asyncio.run(evaluate(action))
```

If the AI service is unreachable, `IntentAnalyzer` automatically falls back to
the deterministic result. The system always produces a valid response.

## Input schema — AgentAction

| Field          | Type            | Required | Description                                      |
|----------------|-----------------|----------|--------------------------------------------------|
| `action_id`    | `str`           | Yes      | Unique identifier for this action                |
| `agent`        | `str`           | Yes      | Agent name (e.g. `"kiro"`)                      |
| `action_type`  | `str`           | Yes      | Type of action (see table below)                 |
| `target`       | `str \| None`   | No       | File path, URL, or resource being acted upon     |
| `command`      | `str \| None`   | No       | Shell command being executed                     |
| `task_context` | `str \| None`   | No       | What the agent is trying to accomplish           |
| `metadata`     | `dict`          | No       | Additional action-specific metadata              |

### Recognised action types

| Action type          | Meaning                         |
|----------------------|---------------------------------|
| `file_read`          | Read a file                     |
| `file_write`         | Write or create a file          |
| `file_delete`        | Delete a file                   |
| `command_execute`    | Execute a shell command         |
| `network_request`    | Make an HTTP/HTTPS request      |
| `package_install`    | Install a package               |
| `process_spawn`      | Spawn a new process             |

## Output schemas

### ContextResult

```python
{
  "resource_type": "ssh_configuration",      # specific resource label
  "resource_category": "ssh_resource",       # broad category
  "sensitivity": "HIGH",                     # LOW | MEDIUM | HIGH | CRITICAL
  "contains_credentials": false,
  "is_system_resource": false,
  "is_destructive": false,
  "is_network_operation": false,
  "requires_special_attention": true,
  "reason": "Path matches an SSH configuration file."
}
```

### IntentResult

```python
{
  "intent": "access_sensitive_configuration",
  "confidence": 0.90,
  "reason": "The agent is attempting to access an SSH resource '/home/user/.ssh/config'.",
  "source": "deterministic",                 # deterministic | ai_service | fallback
  "alternative_intent": null,
  "alternative_confidence": null
}
```

### Sensitivity levels

| Level      | Meaning                                                  |
|------------|----------------------------------------------------------|
| `LOW`      | Normal project file, no security concern                 |
| `MEDIUM`   | Configuration, package manifest, shell profile           |
| `HIGH`     | SSH config, .env file, system path, shell history        |
| `CRITICAL` | SSH private key, cloud credentials, destructive command  |

### Intent categories

| Category                         | Triggered by                                           |
|----------------------------------|--------------------------------------------------------|
| `read_project_file`              | Reading a normal source file                           |
| `modify_project_file`            | Writing to a normal source file                        |
| `access_configuration`           | Reading a config file (no secrets)                     |
| `access_sensitive_configuration` | Reading .env, SSH config, database config              |
| `access_credentials`             | Reading SSH keys, AWS credentials, token files         |
| `install_dependency`             | pip/npm/cargo install commands                         |
| `execute_command`                | General shell command execution                        |
| `network_access`                 | HTTP requests, curl, network_request action type       |
| `delete_resource`                | file_delete action, rm -rf, DROP TABLE                 |
| `modify_system`                  | Writing to system paths (/etc/, /proc/)                |
| `spawn_process`                  | process_spawn action type                              |
| `unknown`                        | No rule matched — manual review recommended            |

## Integrating Person 2's AI service

Implement `AIIntentAnalyzer` and pass it to `IntentAnalyzer`:

```python
from paladin.intent.service import AIIntentAnalyzer, ServiceUnavailableError
from paladin.schemas.intent import IntentCategory, IntentResult, IntentSource

class MyAIAnalyzer(AIIntentAnalyzer):
    async def analyze(self, action, context) -> IntentResult:
        # Call Person 2's endpoint here
        response = await my_http_client.post("/analyze/intent", json={
            "action": action.model_dump(),
            "context": context.model_dump(),
        })
        data = response.json()
        return IntentResult(
            intent=IntentCategory(data["intent"]),
            confidence=data["confidence"],
            reason=data["reason"],
            source=IntentSource.AI_SERVICE,
        )

    def is_available(self) -> bool:
        return True  # your health-check logic

analyzer = IntentAnalyzer(ai_service=MyAIAnalyzer())
```

Or use the provided `HttpAIAnalyzer` scaffold by passing `base_url` and `api_key`.

## Consuming the output in downstream engines

```python
context, intent = context_engine.analyze(action), intent_analyzer.analyze_sync(action, ctx)

# Policy Engine
if context.sensitivity == "CRITICAL":
    return REQUIRE_APPROVAL
if context.is_destructive:
    return REQUIRE_APPROVAL

# Risk Engine
risk_input = {
    "sensitivity": context.sensitivity,
    "contains_credentials": context.contains_credentials,
    "is_system_resource": context.is_system_resource,
    "intent_confidence": intent.confidence,
}

# Decision Engine
decision_input = {
    "intent": intent.intent,
    "reason": intent.reason,
    "context": context.model_dump(),
}
```

## Running tests

```bash
cd paladin-engine
pip install -r requirements.txt
pytest paladin/tests/ -v
```

Expected output: all tests pass, no AI service required.

## Adding new patterns

Edit `paladin/context/patterns.py` — add a regex to the appropriate list.
The pattern is compiled once at import time. No other file needs to change.

## Adding new intent rules

Edit `paladin/intent/rules.py` — append a `Rule` to `INTENT_RULES`.
Rules are evaluated in order; place higher-priority rules earlier in the list.
