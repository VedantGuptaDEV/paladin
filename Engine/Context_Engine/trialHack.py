"""
trialHack.py

Receives a plain-string prompt from the front-end, converts it into a
structured JSON object, then feeds it through the Paladin context engine.

Prompt format (plain string):
  "prompt=<id> agent=<name> action=<type> target=<path> cwd=<path>
   os=<os> shell=<shell> parent=<process> user=<username>
   project=<root> task=<description>"

All fields except 'prompt' and 'action' are optional.

Examples:
  python trialHack.py "prompt=req-001 agent=kiro action=file_read target=/home/user/project/src/main.py cwd=/home/user/project os=linux shell=bash parent=kiro-cli user=jaskaran project=/home/user/project"
  echo "prompt=req-002 action=file_read target=/home/user/.ssh" | python trialHack.py

Output:
  Results are automatically saved to trialHack_output.csv in the current directory.
  Each run appends a new row with a timestamp.
"""

import sys
import re
import json
import csv
import os
from datetime import datetime

from paladin.context.engine import ContextEngine
from paladin.context.history import ActionHistory
from paladin.schemas.action import AgentAction

# ── CSV output path ────────────────────────────────────────────────────────────
CSV_OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trialHack_output.csv")

CSV_FIELDNAMES = [
    "timestamp",
    "raw_prompt",
    "action_type",
    "target",
    "agent",
    "sensitivity",
    "target_category",
    "cwd",
]


# ── Step 1: Receive string prompt ─────────────────────────────────────────────

def receive_prompt() -> str:
    """Get the raw string prompt from CLI arg or stdin."""
    if len(sys.argv) > 1:
        return " ".join(sys.argv[1:])
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    print("Usage: python trialHack.py \"prompt=<id> action=<type> target=<path> ...\"")
    sys.exit(1)


# ── Step 2: Parse string → structured JSON dict ───────────────────────────────

# Maps shorthand keys in the prompt string to AgentAction field names
KEY_MAP = {
    "prompt":  "prompt",        # becomes action_id internally
    "agent":   "agent",
    "action":  "action_type",
    "target":  "target",
    "cwd":     "cwd",
    "os":      "os",
    "shell":   "shell",
    "parent":  "parent_process",
    "user":    "user",
    "project": "project_root",
    "task":    "task_context",
    "command": "command",
}

def parse_prompt_to_json(prompt_str: str) -> dict:
    """
    Convert a plain key=value string into a structured JSON-compatible dict.

    Supports:
      - Simple:   key=value
      - Quoted:   key="value with spaces"
      - Fallback: bare text treated as task_context
    """
    # Extract key=value or key="quoted value" pairs
    pattern = r'(\w+)=(?:"([^"]*)"|([\S]+))'
    matches = re.findall(pattern, prompt_str)

    raw = {}
    for key, quoted_val, plain_val in matches:
        raw[key.lower()] = quoted_val if quoted_val else plain_val

    # Map shorthand keys to full field names
    structured = {}
    for short_key, value in raw.items():
        field = KEY_MAP.get(short_key, short_key)
        structured[field] = value

    # Ensure required fields have fallbacks
    structured.setdefault("prompt", "unknown")
    structured.setdefault("action_type", "file_read")
    structured.setdefault("metadata", {})

    return structured


# ── Step 3: JSON dict → AgentAction (no agent_pid, prompt as action_id) ───────

def json_to_agent_action(data: dict) -> AgentAction:
    """Build an AgentAction from the structured JSON. Excludes agent_pid."""
    return AgentAction(
        action_id    = data.get("prompt", "unknown"),
        action_type  = data["action_type"],
        target       = data.get("target"),
        command      = data.get("command"),
        task_context = data.get("task_context"),
        agent        = data.get("agent", "unknown"),
        parent_process = data.get("parent_process"),
        cwd          = data.get("cwd"),
        os           = data.get("os"),
        shell        = data.get("shell"),
        project_root = data.get("project_root"),
        user         = data.get("user"),
        metadata     = data.get("metadata", {}),
        # agent_pid intentionally omitted
    )


# ── Sensitivity thresholds that count as a "flag" ─────────────────────────────
# Engine produces: "normal" | "sensitive" | "critical"
FLAGGED_SENSITIVITIES = {"sensitive", "critical"}

def check_flags(ctx, prompt_id: str, target: str) -> list[str]:
    """
    Return a list of human-readable reasons this prompt was flagged.
    Empty list means no issues.
    """
    reasons = []

    sensitivity = str(ctx.sensitivity).lower()
    if sensitivity in FLAGGED_SENSITIVITIES:
        reasons.append(
            f"sensitivity is '{ctx.sensitivity}' -- prompt '{prompt_id}' "
            f"tried to access a {ctx.target_category} resource: {target!r}"
        )

    if ctx.is_outside_project:
        reasons.append(
            f"target is outside the project root -- prompt '{prompt_id}' "
            f"accessed {target!r} which is not under the project directory"
        )

    return reasons


# ── Step 4: Save result row to CSV ────────────────────────────────────────────

def save_to_csv(data: dict, ctx, raw_prompt: str) -> None:
    """Append a result row to trialHack_output.csv, creating the file if needed."""
    prompt_id   = data.get("prompt", "unknown")
    action_type = data.get("action_type", "unknown")
    target      = data.get("target", "N/A")

    row = {
        "timestamp":       datetime.now().isoformat(timespec="seconds"),
        "raw_prompt":      raw_prompt,
        "action_type":     action_type,
        "target":          target,
        "agent":           data.get("agent", "unknown"),
        "sensitivity":     str(ctx.sensitivity),
        "target_category": str(ctx.target_category),
        "cwd":             data.get("cwd", ""),
    }

    file_exists = os.path.isfile(CSV_OUTPUT_PATH)
    with open(CSV_OUTPUT_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

    print(f"  [saved] {CSV_OUTPUT_PATH}")


# ── Step 5: Run engine & display (same format as original) ────────────────────

def run_and_display(engine: ContextEngine, data: dict, raw_prompt: str, index: int, total: int) -> None:
    action = json_to_agent_action(data)
    ctx = engine.build_context(action)

    prompt_id   = data.get("prompt", "unknown")
    action_type = data.get("action_type", "unknown")
    target      = data.get("target", "N/A")

    print(f"=== ACTION {index}: prompt={prompt_id!r}  type={action_type}  target={target} ===")
    print(f"  raw_prompt       : {raw_prompt}")
    print(f"  sensitivity      : {ctx.sensitivity}")
    print(f"  target_category  : {ctx.target_category}")

    # ── Flag report ───────────────────────────────────────────────────────────
    flags = check_flags(ctx, prompt_id, target)
    if flags:
        print()
        print(f"  [FLAGGED] prompt '{prompt_id}' caused the following issue(s):")
        for reason in flags:
            print(f"     - {reason}")
    else:
        print(f"  [PASS] prompt '{prompt_id}' passed -- no issues detected")

    # ── Auto-save to CSV ──────────────────────────────────────────────────────
    save_to_csv(data, ctx, raw_prompt)

    print()

    # Full JSON dump on the last action
    if index == total:
        print("Full context (last action):")
        print(json.dumps(ctx.to_dict(), indent=2))


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    raw_prompt = receive_prompt()

    # Convert string prompt → JSON
    structured_json = parse_prompt_to_json(raw_prompt)

    print("-- Parsed JSON from prompt --")
    print(json.dumps(structured_json, indent=2))
    print()

    engine = ContextEngine(action_history=ActionHistory())
    run_and_display(engine, structured_json, raw_prompt, index=1, total=1)


if __name__ == "__main__":
    main()
