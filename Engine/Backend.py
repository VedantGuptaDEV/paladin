import sys
import os as _os
import pandas as pd
import Risk_Engine.RiskEngine as risk

_ENGINE_DIR = _os.path.dirname(_os.path.abspath(__file__))
_CSV_PATH   = _os.path.join(_ENGINE_DIR, "Context_Engine", "trialHack_output.csv")

# ── Make paladin_cli importable ───────────────────────────────────────────────
_CLI_DIR = _os.path.join(_ENGINE_DIR, "..", "paladin_cli")
if _CLI_DIR not in sys.path:
    sys.path.insert(0, _CLI_DIR)


def pass_to_kiro(prompt: str) -> None:
    """
    Forward a clean prompt to kiro-cli and render the response in paladin style.

    Imports paladin.py as a module so we get access to its full rendering
    pipeline (ask_and_render, _push, _render_line, ANSI palette, etc.)
    without spawning a second process.
    """
    import importlib.util as _ilu

    paladin_path = _os.path.join(_CLI_DIR, "paladin.py")
    spec = _ilu.spec_from_file_location("paladin", paladin_path)
    paladin = _ilu.module_from_spec(spec)
    spec.loader.exec_module(paladin)

    # Clear any leftover lines from the import-time banner push
    paladin._lines.clear()

    # Render the user bubble then ask kiro
    paladin._push_user_bubble(prompt)
    paladin.ask_and_render(prompt, label="response")

    # Stream rendered output to stdout
    for line in paladin._lines:
        print(line)


# ── Main logic ────────────────────────────────────────────────────────────────

uin = pd.read_csv(_CSV_PATH)

prompt = uin["raw_prompt"].tolist()[-1]

# Risk score
risk_fns = risk.risk_score(prompt)
print(f"risk score: {risk_fns[1]}")

# Tier 2 check — pass the prompt so flag() can forward it if the user approves
t2_out = risk.tier2(risk_fns[0], prompt)

if t2_out == 0:
    # Safe — forward the prompt to kiro-cli via paladin's renderer
    pass_to_kiro(prompt)
elif t2_out == 1:
    # Medium risk — send to LLM (tier 3)
    risk.tier3(uin)
# t2_out == -1 means flagged/blocked; flagger.flag() already ran inside tier2()
