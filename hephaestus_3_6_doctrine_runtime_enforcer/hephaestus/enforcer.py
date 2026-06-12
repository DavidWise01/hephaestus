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


class DoctrineEnforcer:
    def __init__(self, rules): self.l=Ledger(); self.rules=rules; self.actions=[]  # rules: subject->effect
    def enforce(self, subject):
        effect=self.rules.get(subject,"allow")
        rec={"subject":subject,"effect":effect}; self.actions.append(rec)
        self.l.receipt("action_"+effect,subject,rec); return effect
    def health(self):
        return {"actions":len(self.actions),
                "allowed":sum(1 for a in self.actions if a["effect"]=="allow"),
                "denied":sum(1 for a in self.actions if a["effect"]=="deny"),
                "status":"runtime_enforcer","ledger":self.l.verify()}
def seed_demo(td):
    e=DoctrineEnforcer({"export":"deny","destroy":"deny","read":"allow"})
    for s in ["read","export","read","destroy","write"]: e.enforce(s)
    h=e.health()
    return {"health":h,"bundle":bundle(td,"enforcer_bundle.zip",{"health.json":h,"ledger.json":e.l.entries})}
