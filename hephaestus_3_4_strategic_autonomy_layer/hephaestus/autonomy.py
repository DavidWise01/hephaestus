import json, hashlib, zipfile
from pathlib import Path
def digest(o): return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()
class Ledger:
    def __init__(self): self.entries=[]
    def receipt(self, kind, subject, payload):
        prev=self.entries[-1]["entry_hash"] if self.entries else "GENESIS"
        ph=digest(payload); eh=digest({"kind":kind,"subject":subject,"payload_hash":ph,"prev_hash":prev})
        self.entries.append({"kind":kind,"subject":subject,"payload_hash":ph,"prev_hash":prev,"entry_hash":eh}); return eh
    def verify(self):
        prev="GENESIS"
        for i,r in enumerate(self.entries,1):
            exp=digest({"kind":r["kind"],"subject":r["subject"],"payload_hash":r["payload_hash"],"prev_hash":prev})
            if r["prev_hash"]!=prev or r["entry_hash"]!=exp: return {"ok":False,"seq":i}
            prev=r["entry_hash"]
        return {"ok":True,"entries":len(self.entries),"head":prev}
def bundle(td, name, files):
    p=Path(td)/name; p.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(p,"w") as z:
        for n,o in files.items(): z.writestr(n, json.dumps(o, indent=2, default=str))
    return {"path":str(p), "exists":p.exists(), "files":len(files)}


class AutonomyLayer:
    def __init__(self): self.l=Ledger(); self.objective=None; self.steps=[]; self.guardrails=set()
    def guardrail(self, forbidden): self.guardrails.add(forbidden)
    def set_objective(self, text):
        self.objective=text; self.l.receipt("objective_set","autonomy",{"objective":text})
    def plan(self, actions):
        for a in actions:
            sid="step:"+digest({"a":a,"n":len(self.steps)})[:12]
            self.steps.append({"id":sid,"action":a,"state":"planned"}); self.l.receipt("step_planned",sid,{"action":a})
    def execute(self):
        for s in self.steps:
            if s["action"] in self.guardrails:
                s["state"]="blocked"; self.l.receipt("step_blocked",s["id"],{"by":"guardrail"})
            else:
                s["state"]="executed"; self.l.receipt("step_executed",s["id"],s)
        return self.health()
    def health(self):
        return {"objective":self.objective,"steps":len(self.steps),
                "executed":sum(1 for s in self.steps if s["state"]=="executed"),
                "blocked":sum(1 for s in self.steps if s["state"]=="blocked"),
                "status":"autonomy","ledger":self.l.verify()}
def seed_demo(td):
    a=AutonomyLayer(); a.guardrail("delete_evidence"); a.set_objective("harden the grid")
    a.plan(["scan_nodes","apply_patch","delete_evidence","attest"]); a.execute()
    h=a.health()
    return {"health":h,"bundle":bundle(td,"autonomy_bundle.zip",{"health.json":h,"ledger.json":a.l.entries})}
