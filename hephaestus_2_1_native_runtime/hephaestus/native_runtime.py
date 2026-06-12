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


class NativeRuntime:
    def __init__(self): self.l=Ledger(); self.artifacts={}; self.procs={}; self.cpu=0; self.mem=0
    def load(self, name, cost_cpu=10, cost_mem=64):
        aid="art:"+digest({"name":name})[:12]
        self.artifacts[aid]={"id":aid,"name":name,"cpu":cost_cpu,"mem":cost_mem}
        self.l.receipt("artifact_loaded",aid,self.artifacts[aid]); return aid
    def run(self, aid):
        a=self.artifacts[aid]; pid="proc:"+digest({"a":aid,"n":len(self.procs)})[:12]
        self.procs[pid]={"id":pid,"artifact":aid,"state":"running"}
        self.cpu+=a["cpu"]; self.mem+=a["mem"]; self.l.receipt("process_started",pid,self.procs[pid]); return pid
    def stop(self, pid):
        p=self.procs[pid]; a=self.artifacts[p["artifact"]]
        if p["state"]=="running": self.cpu-=a["cpu"]; self.mem-=a["mem"]; p["state"]="stopped"
        self.l.receipt("process_stopped",pid,p)
    def health(self):
        return {"artifacts":len(self.artifacts),"processes":len(self.procs),
                "running":sum(1 for p in self.procs.values() if p["state"]=="running"),
                "cpu_units":self.cpu,"mem_mb":self.mem,"status":"native","ledger":self.l.verify()}
def seed_demo(td):
    rt=NativeRuntime(); a1=rt.load("compiler"); a2=rt.load("monitor")
    p1=rt.run(a1); rt.run(a1); rt.run(a2); rt.stop(p1)
    h=rt.health()
    return {"health":h,"bundle":bundle(td,"native_runtime_bundle.zip",{"health.json":h,"ledger.json":rt.l.entries})}
