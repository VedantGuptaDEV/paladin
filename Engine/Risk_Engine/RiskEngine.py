import numpy as np
from sentence_transformers import SentenceTransformer
import flagger as f
import os as _os

###################################################################################################################################################################################################

#Confidence metric/Rsik Score:

_ASSETS_DIR = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "assets")
MAL_PROMPTS=np.load(_os.path.join(_ASSETS_DIR, "embedded_mal_prompts.npy"))
model=SentenceTransformer("all-MiniLM-L6-v2")

def risk_score(u_prompt:str):
    USER_PROMPT=u_prompt

    #normalize_embeddings makes strings into unit vectors of 384 hyperparameters:
    u_vector=model.encode(USER_PROMPT,normalize_embeddings=True)

    #dot pdt:
    all_risks=np.dot(MAL_PROMPTS, u_vector) #for all cos(theta) = (p_bar . r_bar)/(p . r)
    risk_factor=float(max(all_risks))
    if risk_factor<0:
        risk_score=float(np.log(abs(risk_factor)))*10 #accomodation of -ve values of cos()
    else:
        risk_score=100*risk_factor

    out=(risk_factor,f"{risk_score:.2f}")

    return out #tuple output

#Tier 3:
API_KEY="<Ask jassi for api key>"

def tier3(j_loc:dict): #the string input is the file path of the json file from vedant's code
    print("sent json to LLM")

#Tier 2:
null2green=0.5
green2orange=0.7

def tier2(risk_factor:float):
    if risk_factor<null2green:
        # Safe — caller (Backend.py) will forward prompt to kiro-cli
        return 0
    elif null2green<=risk_factor and risk_factor<=green2orange:
        print("send to LLM")
        return 1
    else:
        f.flag()
        return -1


###################################################################################################################################################################################################