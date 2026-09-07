"""
watcher.py — watches engine/Context_Engine/trialHack_output.csv and processes
each new prompt in-process (no subprocess spawn) so the SentenceTransformer
model is loaded exactly once at startup.

Run from anywhere inside the project — it resolves paths automatically.
    python engine/watcher.py
"""

import os
import sys
import time

# Resolve absolute paths regardless of where the script is called from
ENGINE_DIR   = os.path.dirname(os.path.abspath(__file__))  # .../paladin/engine
PROJECT_ROOT = os.path.dirname(ENGINE_DIR)                  # .../paladin
_CLI_DIR     = os.path.join(PROJECT_ROOT, "paladin_cli")

WATCH_FILE    = os.path.join(ENGINE_DIR, "Context_Engine", "trialHack_output.csv")
POLL_INTERVAL = 1  # seconds

# ── Make engine/ and paladin_cli/ importable ─────────────────────────────────
for _p in (ENGINE_DIR, _CLI_DIR, PROJECT_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── Load heavy dependencies ONCE at startup ───────────────────────────────────
print("[watcher] Loading Risk Engine (SentenceTransformer — one-time) …", flush=True)
import pandas as pd
import Risk_Engine.RiskEngine as risk   # SentenceTransformer loads here, once
import flagger as f
print("[watcher] Risk Engine ready.\n", flush=True)


# ── pass_to_kiro (identical to Backend.py, kept here to avoid re-importing) ──

def pass_to_kiro(prompt: str) -> None:
    """Forward a clean prompt to kiro-cli via paladin's renderer."""
    import importlib.util as _ilu

    paladin_path = os.path.join(_CLI_DIR, "paladin.py")
    spec    = _ilu.spec_from_file_location("paladin", paladin_path)
    paladin = _ilu.module_from_spec(spec)
    spec.loader.exec_module(paladin)

    paladin._lines.clear()
    paladin._push_user_bubble(prompt)
    paladin.ask_and_render(prompt, label="response")

    for line in paladin._lines:
        print(line)


# ── Per-prompt processing (runs in THIS process, model already loaded) ────────

def run_backend() -> None:
    print("[watcher] Change detected — processing prompt …", flush=True)

    try:
        uin    = pd.read_csv(WATCH_FILE)
        prompt = uin["raw_prompt"].tolist()[-1]
    except Exception as exc:
        print(f"[watcher] Failed to read CSV: {exc}\n", flush=True)
        return

    risk_fns = risk.risk_score(prompt)
    print(f"[watcher] risk score: {risk_fns[1]}", flush=True)

    t2_out = risk.tier2(risk_fns[0], prompt)

    if t2_out == 0:
        pass_to_kiro(prompt)
    elif t2_out == 1:
        risk.tier3(uin)
    # t2_out == -1: flagged; flagger.flag() already ran inside tier2()

    print("[watcher] Done.\n", flush=True)


# ── File watcher loop ─────────────────────────────────────────────────────────

def get_mtime(path: str):
    try:
        return os.path.getmtime(path)
    except FileNotFoundError:
        return None


def main() -> None:
    print(f"[watcher] Project root : {PROJECT_ROOT}", flush=True)
    print(f"[watcher] Watching     : {WATCH_FILE}", flush=True)
    print("[watcher] Press Ctrl+C to stop.\n", flush=True)

    if not os.path.exists(WATCH_FILE):
        print("[watcher] WARNING: watched file does not exist yet — will trigger on first creation.", flush=True)

    last_mtime = get_mtime(WATCH_FILE)

    while True:
        time.sleep(POLL_INTERVAL)
        current_mtime = get_mtime(WATCH_FILE)

        if current_mtime is None:
            last_mtime = None
            continue

        if last_mtime is None or current_mtime != last_mtime:
            last_mtime = current_mtime
            run_backend()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[watcher] Stopped.")
