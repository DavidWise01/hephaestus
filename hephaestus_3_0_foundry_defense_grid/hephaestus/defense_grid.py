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


class DefenseGrid:
    def __init__(self): self.l=Ledger(); self.nodes={}; self.incidents={}; self.responses={}
    def add_node(self, name):
        nid="node:"+digest({"name":name})[:12]; self.nodes[nid]={"id":nid,"name":name,"health":"ok"}
        self.l.receipt("node_joined",nid,self.nodes[nid]); return nid
    def incident(self, artifact, severity):
        iid="inc:"+digest({"artifact":artifact,"n":len(self.incidents)})[:12]
        self.incidents[iid]={"id":iid,"artifact":artifact,"severity":severity,"status":"open"}
        self.l.receipt("incident_raised",iid,self.incidents[iid]); return iid
    def coordinate(self, iid):
        votes=[n["id"] for n in self.nodes.values() if n["health"]=="ok"]
        quorum=len(self.nodes)//2+1; approved=len(votes)>=quorum
        rid="resp:"+digest({"i":iid})[:12]
        self.responses[rid]={"id":rid,"incident":iid,"votes":len(votes),"quorum":quorum,"approved":approved}
        if approved: self.incidents[iid]["status"]="contained"
        self.l.receipt("response_coordinated",rid,self.responses[rid]); return self.responses[rid]
    def health(self):
        return {"nodes":len(self.nodes),"incidents":len(self.incidents),"responses":len(self.responses),
                "contained":sum(1 for i in self.incidents.values() if i["status"]=="contained"),
                "status":"defense_grid","ledger":self.l.verify()}
def seed_demo(td):
    g=DefenseGrid(); [g.add_node(n) for n in ("alpha","bravo","charlie")]
    i1=g.incident("artifact:x",80); g.incident("artifact:y",40); g.coordinate(i1)
    h=g.health()
    return {"health":h,"bundle":bundle(td,"defense_grid_bundle.zip",{"health.json":h,"ledger.json":g.l.entries})}
