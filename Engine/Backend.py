import pandas as pd
import Risk_Engine.RiskEngine as risk

uin=pd.read_csv("engine\\Context_Engine\\trialHack_output.csv")

prompt=uin["prompt"]

#Risk score:
risk_fns=risk.risk_score(prompt)
print("risk score:",risk_fns[1])

#tier 2 check:
t2_out=risk.tier2(risk_fns[0])

#tier 3 check:
if t2_out==1:
    risk.tier3(uin)