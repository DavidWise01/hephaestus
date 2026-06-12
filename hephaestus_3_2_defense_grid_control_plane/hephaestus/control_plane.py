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


class ControlPlane:
    def __init__(self): self.l=Ledger(); self.nodes={}; self.desired=None
    def register(self, name):
        nid="node:"+digest({"name":name})[:12]; self.nodes[nid]={"id":nid,"name":name,"config":"v1"}
        self.l.receipt("node_registered",nid,self.nodes[nid]); return nid
    def push_config(self, version):
        self.desired=version; self.l.receipt("config_pushed","control_plane",{"version":version})
    def reconcile(self):
        for n in self.nodes.values():
            if n["config"]!=self.desired:
                n["config"]=self.desired; self.l.receipt("node_reconciled",n["id"],{"to":self.desired})
        return self.health()
    def health(self):
        conv=sum(1 for n in self.nodes.values() if n["config"]==self.desired)
        return {"nodes":len(self.nodes),"desired":self.desired,"converged":conv,
                "drift":len(self.nodes)-conv,"status":"control_plane","ledger":self.l.verify()}
def seed_demo(td):
    cp=ControlPlane(); [cp.register(n) for n in ("c1","c2","c3")]
    cp.push_config("v2"); cp.reconcile()
    h=cp.health()
    return {"health":h,"bundle":bundle(td,"control_plane_bundle.zip",{"health.json":h,"ledger.json":cp.l.entries})}
