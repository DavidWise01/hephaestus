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


class SovereignKernel:
    # legitimacy rule: a sovereign decision needs the named authority granted + the ledger intact
    def __init__(self): self.l=Ledger(); self.authorities={}; self.subsystems={}; self.decisions=[]
    def grant(self, authority):
        aid="authority:"+authority; self.authorities[aid]={"id":aid,"name":authority}
        self.l.receipt("authority_granted",aid,self.authorities[aid]); return aid
    def bind(self, subsystem, authority):
        aid="authority:"+authority
        ok=aid in self.authorities
        self.subsystems[subsystem]={"subsystem":subsystem,"authority":aid,"bound":ok}
        self.l.receipt("subsystem_bound",subsystem,self.subsystems[subsystem]); return ok
    def decide(self, action, required_authority):
        aid="authority:"+required_authority
        legitimate = aid in self.authorities and self.l.verify()["ok"]
        d={"action":action,"required":aid,"legitimate":legitimate,
           "verdict":"enacted" if legitimate else "rejected"}
        self.decisions.append(d); self.l.receipt("sovereign_decision",action,d); return d
    def health(self):
        return {"root_authorities":len(self.authorities),"bound_subsystems":sum(1 for s in self.subsystems.values() if s["bound"]),
                "authority_records":len(self.subsystems),"sovereign_decisions":len(self.decisions),
                "enacted":sum(1 for d in self.decisions if d["verdict"]=="enacted"),
                "rejected":sum(1 for d in self.decisions if d["verdict"]=="rejected"),
                "kernel_active":True,"status":"sovereign","ledger":self.l.verify()}
def seed_demo(td):
    k=SovereignKernel()
    for a in ("doctrine","enforcement","audit","recovery","command"): k.grant(a)
    for s,a in [("doctrine_engine","doctrine"),("enforcement_mesh","enforcement"),
                ("mesh_auditor","audit"),("recovery_engine","recovery"),("command_authority","command")]:
        k.bind(s,a)
    k.decide("ratify_doctrine","doctrine")        # legitimate
    k.decide("seize_unbound","treasury")          # rejected: no such authority
    h=k.health()
    return {"health":h,"bundle":bundle(td,"sovereign_bundle.zip",{"health.json":h,"ledger.json":k.l.entries})}
