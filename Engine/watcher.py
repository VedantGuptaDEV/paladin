"""
watcher.py — watches engine/Context_Engine/trialHack_output.csv and runs
Backend.py every time the file is modified.

Run from anywhere inside the project — it resolves paths automatically.
    python engine/watcher.py
"""

import os
import sys
import time
import subprocess

# Resolve absolute paths regardless of where the script is called from
ENGINE_DIR   = os.path.dirname(os.path.abspath(__file__))          # .../paladin/engine
PROJECT_ROOT = os.path.dirname(ENGINE_DIR)                          # .../paladin

WATCH_FILE    = os.path.join(ENGINE_DIR, "Context_Engine", "trialHack_output.csv")
BACKEND       = os.path.join(ENGINE_DIR, "Backend.py")
POLL_INTERVAL = 1  # seconds

def get_mtime(path):
    try:
        return os.path.getmtime(path)
    except FileNotFoundError:
        return None

def run_backend():
    print("[watcher] Change detected — running Backend.py ...", flush=True)

    # Backend.py uses paths like "engine\\..." so cwd must be the project root.
    # RiskEngine.py / flagger.py live in engine/, so we add engine/ to PYTHONPATH.
    env = os.environ.copy()
    existing_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = ENGINE_DIR + (os.pathsep + existing_pp if existing_pp else "")

    result = subprocess.run(
        [sys.executable, BACKEND],
        cwd=PROJECT_ROOT,
        env=env,
    )

    if result.returncode == 0:
        print("[watcher] Backend.py finished successfully.\n", flush=True)
    else:
        print(f"[watcher] Backend.py exited with code {result.returncode}.\n", flush=True)

def main():
    print(f"[watcher] Project root : {PROJECT_ROOT}", flush=True)
    print(f"[watcher] Watching     : {WATCH_FILE}", flush=True)
    print(f"[watcher] Will run     : {BACKEND}", flush=True)
    print("[watcher] Press Ctrl+C to stop.\n", flush=True)

    if not os.path.exists(WATCH_FILE):
        print(f"[watcher] WARNING: watched file does not exist yet — will trigger on first creation.", flush=True)

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
