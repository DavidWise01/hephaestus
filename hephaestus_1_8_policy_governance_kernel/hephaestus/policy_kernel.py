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


class PolicyKernel:
    def __init__(self): self.l=Ledger(); self.policies={}; self.decisions=[]
    def register(self, name, key, effect, priority=0):
        pid="pol:"+digest({"name":name,"key":key})[:12]
        self.policies[pid]={"id":pid,"name":name,"key":key,"effect":effect,"priority":priority}
        self.l.receipt("policy_registered",pid,self.policies[pid]); return pid
    def evaluate(self, subject, attrs):
        hits=sorted([p for p in self.policies.values() if attrs.get(p["key"])],
                    key=lambda p:-p["priority"])
        effect=hits[0]["effect"] if hits else "allow"  # default-allow unless a policy matches
        d={"subject":subject,"attrs":attrs,"matched":[h["id"] for h in hits],"effect":effect}
        self.decisions.append(d); self.l.receipt("decision",subject,d); return d
    def health(self):
        return {"policies":len(self.policies),"decisions":len(self.decisions),
                "denied":sum(1 for d in self.decisions if d["effect"]=="deny"),
                "status":"active","ledger":self.l.verify()}
def seed_demo(td):
    k=PolicyKernel()
    k.register("no-untrusted","untrusted","deny",priority=10)
    k.register("block-tamper","tampered","deny",priority=20)
    k.register("audit-large","large","allow",priority=1)
    k.evaluate("artifact:a",{"large":True})
    k.evaluate("artifact:b",{"untrusted":True})
    k.evaluate("artifact:c",{"tampered":True,"untrusted":True})
    k.evaluate("artifact:d",{})
    h=k.health()
    return {"health":h,"bundle":bundle(td,"policy_kernel_bundle.zip",{"health.json":h,"ledger.json":k.l.entries})}
