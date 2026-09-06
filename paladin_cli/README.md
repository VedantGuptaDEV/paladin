# paladin CLI

Interactive AI security agent for your terminal — like Claude Code or Kiro CLI.

Every command constructs a prompt and sends it to `kiro-cli`, which handles the AI response live in your terminal.

---

## Prerequisites

Install and log in to kiro-cli:
```bash
# Install from https://kiro.ai, then:
kiro login
```

## Setup

```bash
cd paladin_cli
pip install -r requirements.txt
```

Make it executable (optional):
```bash
chmod +x paladin.py
# then run as:
./paladin.py
# or add an alias:
alias paladin="python /path/to/paladin_cli/paladin.py"
```

---

## Usage

### Interactive REPL
```bash
python paladin.py
```
Starts a full interactive session. Type any prompt and hit Enter — it streams directly through kiro-cli. Type `/help` inside the REPL to see all shortcuts.

### One-shot prompt
```bash
python paladin.py "explain what this project does"
```

### Subcommands

| Command | Description |
|---|---|
| `paladin init` | Initialize paladin in the current project |
| `paladin start` | Start a new agent session |
| `paladin status` | Show current session status |
| `paladin run` | Run the agent on a task (prompts for task if not given) |
| `paladin approvals` | List pending approvals |
| `paladin approve <id>` | Approve an action by ID |
| `paladin deny <id>` | Deny an action by ID |
| `paladin activity` | Show session activity log |
| `paladin activity <id>` | Show activity for a specific session |
| `paladin policy list` | List all policies |
| `paladin policy add` | Add a new policy interactively |
| `paladin policy test` | Test a prompt against policies |
| `paladin config` | Show / edit configuration |
| `paladin doctor` | Check environment health |
| `paladin version` | Show version info |

### REPL shortcuts

| Shortcut | Action |
|---|---|
| `/help` | Show help |
| `/exit` or `/quit` | Exit |
| `/clear` | Clear screen |
| `/session` | Show current session info |
| `/model <name>` | Switch model for this session |

---

## Config

Config is stored at `~/.paladin/config.json`. Edit it directly or use `paladin config`.

```json
{
  "model": null,
  "agent": "paladin",
  "current_session": null
}
```

### Theme Configuration

Paladin uses a consistent black background with bright colors optimized for readability and contrast. Run the color test to verify everything displays correctly:

```bash
# Test colors to verify theme is working correctly
python test_colors.py
```
```

## How it works

Each command builds a structured prompt describing the intent (e.g. "list pending approvals", "approve action ID xyz") and sends it to `kiro-cli`, which handles all AI inference and streams the response back to your terminal — exactly like kiro-cli's own chat interface.

## License

MIT
