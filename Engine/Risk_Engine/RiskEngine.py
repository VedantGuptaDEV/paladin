import numpy as np
from sentence_transformers import SentenceTransformer
import flagger as f
import os as _os

###################################################################################################################################################################################################

# Confidence metric / Risk Score:

_ASSETS_DIR = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "assets")
MAL_PROMPTS = np.load(_os.path.join(_ASSETS_DIR, "embedded_mal_prompts.npy"))
model = SentenceTransformer("all-MiniLM-L6-v2")

def risk_score(u_prompt: str):
    USER_PROMPT = u_prompt

    # normalize_embeddings makes strings into unit vectors of 384 dimensions:
    u_vector = model.encode(USER_PROMPT, normalize_embeddings=True)

    # dot product: cos(theta) = (p_bar . r_bar) / (|p| |r|)
    all_risks = np.dot(MAL_PROMPTS, u_vector)
    risk_factor = float(max(all_risks))
    if risk_factor < 0:
        score = float(np.log(abs(risk_factor))) * 10  # accommodate negative cos values
    else:
        score = 100 * risk_factor

    return (risk_factor, f"{score:.2f}")  # tuple output


# Tier 3:
API_KEY = "<Ask jassi for api key>"

def tier3(j_loc: dict):
    print("sent json to LLM")


# Tier 2:
null2green   = 0.5
green2orange = 0.7

def tier2(risk_factor: float, prompt: str = ""):
    if risk_factor < null2green:
        # Safe — caller will forward prompt to kiro-cli
        return 0
    elif null2green <= risk_factor <= green2orange:
        print("send to LLM")
        return 1
    else:
        f.flag(prompt)
        return -1


###################################################################################################################################################################################################
