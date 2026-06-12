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


class DoctrineEngine:
    def __init__(self): self.l=Ledger(); self.doctrines={}; self.order=[]; self.conflicts=[]
    def register(self, subject, effect, priority):
        did="doc:"+digest({"subject":subject,"effect":effect,"n":len(self.doctrines)})[:12]
        self.doctrines[did]={"id":did,"subject":subject,"effect":effect,"priority":priority}
        self.l.receipt("doctrine_registered",did,self.doctrines[did]); return did
    def compile(self):
        self.order=[d["id"] for d in sorted(self.doctrines.values(), key=lambda d:-d["priority"])]
        # conflict = same subject, opposite effect
        bysub={}
        for d in self.doctrines.values(): bysub.setdefault(d["subject"],set()).add(d["effect"])
        self.conflicts=[s for s,eff in bysub.items() if {"allow","deny"}<=eff]
        out={"execution_order":self.order,"conflicts":self.conflicts}
        self.l.receipt("doctrine_compiled","engine",out); return out
    def evaluate(self, subject):
        for did in self.order:
            d=self.doctrines[did]
            if d["subject"]==subject: return {"subject":subject,"effect":d["effect"],"by":did}
        return {"subject":subject,"effect":"allow","by":None}
    def health(self):
        return {"doctrines":len(self.doctrines),"compiled":len(self.order),"conflicts":len(self.conflicts),
                "status":"doctrine_engine","ledger":self.l.verify()}
def seed_demo(td):
    e=DoctrineEngine()
    e.register("export","deny",90); e.register("export","allow",10)  # conflicting pair
    e.register("read","allow",50); e.register("destroy","deny",99)
    e.compile(); e.evaluate("export")
    h=e.health()
    return {"health":h,"bundle":bundle(td,"doctrine_bundle.zip",{"health.json":h,"ledger.json":e.l.entries})}
