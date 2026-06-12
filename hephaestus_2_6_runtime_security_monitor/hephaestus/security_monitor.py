
import json, hashlib, zipfile
from pathlib import Path

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()

class SecurityMonitor:
    def __init__(self, incidents="incidents"):
        self.incidents_dir = Path(incidents); self.incidents_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts = {}; self.policies = {}; self.activity = []; self.access = []
        self.anomalies = []; self.drift = []; self.kills = []; self.quarantine = {}
        self.incidents = []; self.ledger = []

    def receipt(self, kind, subject, payload):
        prev = self.ledger[-1]["entry_hash"] if self.ledger else "GENESIS"
        ph = digest(payload); eh = digest({"kind":kind,"subject":subject,"payload_hash":ph,"prev_hash":prev})
        self.ledger.append({"kind":kind,"subject":subject,"payload_hash":ph,"prev_hash":prev,"entry_hash":eh})

    def verify_ledger(self):
        prev="GENESIS"
        for i,r in enumerate(self.ledger,1):
            exp=digest({"kind":r["kind"],"subject":r["subject"],"payload_hash":r["payload_hash"],"prev_hash":prev})
            if r["prev_hash"]!=prev or r["entry_hash"]!=exp:
                return {"ok":False,"seq":i}
            prev=r["entry_hash"]
        return {"ok":True,"entries":len(self.ledger),"head":prev}

    def register(self, name, permissions=None):
        aid="artifact:"+digest(name)[:16]
        self.artifacts[aid]={"id":aid,"name":name,"status":"running","health":"ok","permissions":permissions or []}
        self.receipt("artifact_registered",aid,self.artifacts[aid]); return {"artifact":aid}

    def policy(self, aid, allowed=None, max_network=10, file_write=False):
        self.policies[aid]={"artifact":aid,"allowed":allowed or ["network:read","state:read"],"max_network":max_network,"file_write":file_write}
        self.receipt("policy_set",aid,self.policies[aid]); return self.policies[aid]

    def incident(self, aid, reason, evidence):
        iid="incident:"+digest({"aid":aid,"reason":reason,"n":len(self.incidents)})[:16]
        rec={"id":iid,"artifact":aid,"reason":reason,"evidence":evidence,"status":"open"}
        self.incidents.append(rec)
        (self.incidents_dir/(iid.replace(":","_")+".json")).write_text(json.dumps(rec,indent=2,default=str))
        self.receipt("security_incident",iid,rec); return rec

    def quarantine_artifact(self, aid, reason):
        if aid in self.artifacts:
            self.artifacts[aid]["status"]="quarantined"; self.artifacts[aid]["health"]="isolated"
        rec={"artifact":aid,"reason":reason,"status":"quarantined"}
        self.quarantine[aid]=rec
        self.incident(aid,reason,rec)
        self.receipt("auto_quarantine",aid,rec); return rec

    def anomaly(self, aid, reason, evidence):
        rec={"id":"anomaly:"+digest({"aid":aid,"reason":reason,"n":len(self.anomalies)})[:16],"artifact":aid,"reason":reason,"evidence":evidence,"severity":"high"}
        self.anomalies.append(rec); self.receipt("anomaly_detected",rec["id"],rec)
        self.quarantine_artifact(aid,reason); return rec

    def log(self, aid, action, resource, detail=None):
        ev={"id":"activity:"+digest({"aid":aid,"action":action,"resource":resource,"n":len(self.activity)})[:16],"artifact":aid,"action":action,"resource":resource,"detail":detail or {}}
        self.activity.append(ev); self.receipt("activity_logged",ev["id"],ev)
        pol=self.policies.get(aid,{})
        perm=f"{resource}:{action}"
        if perm not in pol.get("allowed",[]):
            self.drift.append({"artifact":aid,"permission":perm,"event":ev})
            self.anomaly(aid,"permission_drift",ev)
        if resource=="file" and action=="write" and not pol.get("file_write",False):
            self.anomaly(aid,"blocked_file_write",ev)
        return ev

    def monitor_access(self, aid, access_type, target):
        ev={"id":"access:"+digest({"aid":aid,"type":access_type,"target":target,"n":len(self.access)})[:16],"artifact":aid,"type":access_type,"target":target}
        self.access.append(ev); self.receipt("access_monitored",ev["id"],ev)
        if access_type=="network":
            count=len([x for x in self.access if x["artifact"]==aid and x["type"]=="network"])
            limit=self.policies.get(aid,{}).get("max_network",10)
            if count>limit:
                self.anomaly(aid,"network_threshold_exceeded",{"count":count,"limit":limit})
        return ev

    def kill(self, aid, reason):
        if aid in self.artifacts:
            self.artifacts[aid]["status"]="killed"; self.artifacts[aid]["health"]="stopped"
        ev={"artifact":aid,"reason":reason,"status":"killed"}
        self.kills.append(ev); self.receipt("kill_switch",aid,ev); return ev

    def status(self):
        return {"artifacts":len(self.artifacts),"running":len([a for a in self.artifacts.values() if a["status"]=="running"]),"quarantined":len(self.quarantine),"policies":len(self.policies),"activity_events":len(self.activity),"access_events":len(self.access),"anomalies":len(self.anomalies),"permission_drift":len(self.drift),"kill_events":len(self.kills),"incidents":len(self.incidents),"ledger":self.verify_ledger()}

    def dashboard(self):
        return {"version":"2.6.0","status":self.status(),"artifacts":self.artifacts,"policies":self.policies,"activity":self.activity,"access_events":self.access,"anomalies":self.anomalies,"permission_drift":self.drift,"kill_events":self.kills,"quarantine":self.quarantine,"incidents":self.incidents}

    def export(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            for name,obj in {"security_dashboard.json":self.dashboard(),"artifacts.json":self.artifacts,"policies.json":self.policies,"activity_logs.json":self.activity,"access_events.json":self.access,"anomalies.json":self.anomalies,"permission_drift.json":self.drift,"kill_events.json":self.kills,"quarantine.json":self.quarantine,"incidents.json":self.incidents,"ledger.json":self.ledger}.items():
                z.writestr(name,json.dumps(obj,indent=2,default=str))
            for p in sorted(self.incidents_dir.glob("*.json")):
                z.write(p,arcname="incidents/"+p.name)
        return {"bundle":str(out),"exists":out.exists()}

def seed_demo(td):
    m=SecurityMonitor(Path(td)/"incidents")
    good=m.register("operator-dashboard",["network:read","state:read"])
    bad=m.register("experimental-worker",["network:read","state:read","file:write"])
    m.policy(good["artifact"],["network:read","state:read"],max_network=3)
    m.policy(bad["artifact"],["network:read","state:read"],max_network=1,file_write=False)
    m.log(good["artifact"],"read","network",{"url":"/api/status"})
    m.monitor_access(good["artifact"],"network","/api/status")
    m.log(bad["artifact"],"write","file",{"path":"/tmp/escape"})
    m.monitor_access(bad["artifact"],"network","external://one")
    m.monitor_access(bad["artifact"],"network","external://two")
    kill=m.kill(bad["artifact"],"operator_confirmed_security_stop")
    bundle=m.export(Path(td)/"runtime_security_monitor_bundle.zip")
    return {"good":good,"bad":bad,"kill":kill,"status":m.status(),"bundle":bundle}
