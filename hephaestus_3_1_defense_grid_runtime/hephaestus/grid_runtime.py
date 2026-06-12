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


class GridRuntime:
    def __init__(self): self.l=Ledger(); self.nodes=[]; self.tasks={}
    def add_node(self, name):
        nid="node:"+digest({"name":name})[:12]; self.nodes.append(nid)
        self.l.receipt("node_ready",nid,{"name":name}); return nid
    def schedule(self, kind):
        tid="task:"+digest({"kind":kind,"n":len(self.tasks)})[:12]
        node=self.nodes[len(self.tasks)%len(self.nodes)]  # round-robin
        self.tasks[tid]={"id":tid,"kind":kind,"node":node,"state":"scheduled"}
        self.l.receipt("task_scheduled",tid,self.tasks[tid]); return tid
    def run_all(self):
        for t in self.tasks.values():
            t["state"]="done"; self.l.receipt("task_completed",t["id"],t)
    def health(self):
        return {"nodes":len(self.nodes),"tasks":len(self.tasks),
                "completed":sum(1 for t in self.tasks.values() if t["state"]=="done"),
                "status":"grid_runtime","ledger":self.l.verify()}
def seed_demo(td):
    rt=GridRuntime(); [rt.add_node(n) for n in ("g1","g2","g3")]
    [rt.schedule(k) for k in ("scan","patch","quarantine","scan","attest")]; rt.run_all()
    h=rt.health()
    return {"health":h,"bundle":bundle(td,"grid_runtime_bundle.zip",{"health.json":h,"ledger.json":rt.l.entries})}
