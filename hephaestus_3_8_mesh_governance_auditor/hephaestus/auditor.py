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


class MeshAuditor:
    def __init__(self): self.l=Ledger(); self.findings=[]
    def audit(self, nodes, expected_hash):
        drift=[n["id"] for n in nodes if n.get("rule_hash")!=expected_hash]
        f={"expected":expected_hash,"drift_nodes":drift,"clean":not drift}
        self.findings.append(f); self.l.receipt("audit",expected_hash,f); return f
    def health(self):
        last=self.findings[-1] if self.findings else {"clean":None}
        return {"audits":len(self.findings),
                "drift_found":sum(len(f["drift_nodes"]) for f in self.findings),
                "final_clean":last["clean"],"status":"mesh_auditor","ledger":self.l.verify()}
def seed_demo(td):
    a=MeshAuditor(); good="HASHGOOD"
    nodes=[{"id":"n1","rule_hash":good},{"id":"n2","rule_hash":good},{"id":"n3","rule_hash":"STALE"}]
    a.audit(nodes, good)                       # finds 1 drift
    for n in nodes: n["rule_hash"]=good        # resync
    a.audit(nodes, good)                       # clean
    h=a.health()
    return {"health":h,"bundle":bundle(td,"auditor_bundle.zip",{"health.json":h,"ledger.json":a.l.entries})}
