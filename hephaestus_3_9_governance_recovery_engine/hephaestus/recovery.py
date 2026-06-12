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


class RecoveryEngine:
    def __init__(self):
        self.l=Ledger(); self.repair_plans=[]; self.doctrine_resyncs=[]
        self.quorum_recoveries=[]; self.policy_rollbacks=[]; self.remediations=[]
    def detect_and_recover(self, fault):
        kind=fault["kind"]; fid="fault:"+digest(fault)[:12]
        self.l.receipt("fault_detected",fid,fault)
        plan={"fault":fid,"kind":kind,"steps":["isolate","restore_from_ledger","verify"]}
        self.repair_plans.append(plan); self.l.receipt("repair_planned",fid,plan)
        out={"fault":fid,"kind":kind}
        if kind=="drift": self.doctrine_resyncs.append(out)
        elif kind=="quorum_loss": self.quorum_recoveries.append(out)
        elif kind=="policy_regression": self.policy_rollbacks.append(out)
        self.remediations.append(out); self.l.receipt("remediated",fid,out); return out
    def health(self):
        return {"repair_plans":len(self.repair_plans),"doctrine_resyncs":len(self.doctrine_resyncs),
                "quorum_recoveries":len(self.quorum_recoveries),"remediations":len(self.remediations),
                "policy_rollbacks":len(self.policy_rollbacks),"receipts":len(self.l.entries),
                "status":"recovered","ledger":self.l.verify()}
def seed_demo(td):
    r=RecoveryEngine()
    for f in [{"kind":"drift","node":"n3"},{"kind":"quorum_loss","mesh":"m"},{"kind":"policy_regression","pol":"p1"}]:
        r.detect_and_recover(f)
    h=r.health()
    return {"health":h,"bundle":bundle(td,"recovery_bundle.zip",{"health.json":h,"ledger.json":r.l.entries})}
