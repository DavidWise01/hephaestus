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


class EnforcementMesh:
    def __init__(self): self.l=Ledger(); self.nodes={}; self.rule_hash=None; self.violations=[]; self.overrides=[]
    def add_node(self, name):
        nid="node:"+digest({"name":name})[:12]; self.nodes[nid]={"id":nid,"name":name,"rule_hash":None}
        self.l.receipt("node_joined",nid,self.nodes[nid]); return nid
    def push_rules(self, ruleset):
        self.rule_hash=digest(ruleset)
        for n in self.nodes.values(): n["rule_hash"]=self.rule_hash
        self.l.receipt("rules_synced","mesh",{"rule_hash":self.rule_hash})
    def violation(self, node, subject):
        v={"node":node,"subject":subject}; self.violations.append(v); self.l.receipt("violation",node,v)
    def override(self, subject):
        quorum=len(self.nodes)*3//4 + (0 if (len(self.nodes)*3)%4==0 else 1)
        votes=len(self.nodes)  # all healthy nodes vote
        approved=votes>=quorum; o={"subject":subject,"votes":votes,"quorum":quorum,"approved":approved}
        self.overrides.append(o); self.l.receipt("override",subject,o); return o
    def synced(self): return all(n["rule_hash"]==self.rule_hash for n in self.nodes.values())
    def health(self):
        return {"nodes":len(self.nodes),"rule_sync":self.synced(),"violations":len(self.violations),
                "overrides":len(self.overrides),
                "overrides_approved":sum(1 for o in self.overrides if o["approved"]),
                "status":"enforcement_mesh","ledger":self.l.verify()}
def seed_demo(td):
    m=EnforcementMesh(); [m.add_node(n) for n in ("m1","m2","m3","m4")]
    m.push_rules({"export":"deny","destroy":"deny"})
    m.violation(list(m.nodes)[0],"export"); m.violation(list(m.nodes)[1],"destroy")
    m.override("export")
    h=m.health()
    return {"health":h,"bundle":bundle(td,"mesh_bundle.zip",{"health.json":h,"ledger.json":m.l.entries})}
