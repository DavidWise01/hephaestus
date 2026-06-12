
import json, hashlib, zipfile
from pathlib import Path

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()

class Pipeline:
    def __init__(self, receipts="receipts"):
        self.receipts_dir = Path(receipts); self.receipts_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts = {}; self.gates = {}; self.trust = {}; self.installs = {}
        self.approvals = {}; self.risks = {}; self.quarantine = {}; self.promotions = {}
        self.rollbacks = {}; self.runs = {}; self.receipts = []; self.ledger = []

    def receipt(self, kind, subject, payload):
        prev = self.ledger[-1]["entry_hash"] if self.ledger else "GENESIS"
        ph = digest(payload); eh = digest({"kind":kind,"subject":subject,"payload_hash":ph,"prev_hash":prev})
        row = {"kind":kind,"subject":subject,"payload_hash":ph,"prev_hash":prev,"entry_hash":eh}
        self.ledger.append(row); self.receipts.append(row)
        (self.receipts_dir/(eh[:16]+".json")).write_text(json.dumps(row, indent=2))
        return row

    def verify_ledger(self):
        prev = "GENESIS"
        for i, r in enumerate(self.ledger, 1):
            exp = digest({"kind":r["kind"],"subject":r["subject"],"payload_hash":r["payload_hash"],"prev_hash":prev})
            if r["prev_hash"] != prev or r["entry_hash"] != exp:
                return {"ok":False, "seq":i}
            prev = r["entry_hash"]
        return {"ok":True, "entries":len(self.ledger), "head":prev}

    def intake(self, name, version, publisher, content, metadata=None):
        aid = "artifact:" + digest({"name":name,"version":version,"publisher":publisher})[:16]
        self.artifacts[aid] = {"id":aid,"name":name,"version":version,"publisher":publisher,"hash":hashlib.sha256(content.encode()).hexdigest(),"metadata":metadata or {},"status":"intake"}
        self.receipt("artifact_intake", aid, self.artifacts[aid])
        return {"artifact":aid}

    def score(self, aid):
        a = self.artifacts[aid]; s = 10
        if not a["publisher"].startswith("trusted"): s += 30
        if a["metadata"].get("network") == "required": s += 15
        if a["metadata"].get("privileged"): s += 40
        if a["metadata"].get("experimental"): s += 20
        out = {"artifact":aid,"score":min(s,100),"level":"low" if s<40 else "medium" if s<80 else "high"}
        self.risks[aid] = out; self.receipt("risk_scored", aid, out); return out

    def policy(self, aid, action):
        risk = self.risks.get(aid) or self.score(aid)
        out = {"artifact":aid,"action":action,"decision":"allow" if risk["score"] < 80 else "deny","risk":risk}
        gid = "policy:" + digest({"artifact":aid,"action":action})[:16]
        self.gates[gid] = out; self.receipt("policy_gate", gid, out); return out

    def verify_trust(self, aid):
        a = self.artifacts[aid]
        out = {"artifact":aid,"verified":not a["metadata"].get("tampered", False),"reason":"ok"}
        if not out["verified"]: out["reason"] = "tampered"
        self.trust[aid] = out; self.receipt("trust_verified", aid, out); return out

    def install(self, aid):
        p = self.policy(aid, "install"); t = self.trust.get(aid) or self.verify_trust(aid)
        out = {"artifact":aid,"status":"installed" if p["decision"]=="allow" and t["verified"] else "blocked","policy":p,"trust":t}
        self.installs[aid] = out; self.artifacts[aid]["status"] = out["status"]
        self.receipt("marketplace_install", aid, out); return out

    def approve_execution(self, aid):
        p = self.policy(aid, "execute")
        installed = self.installs.get(aid, {}).get("status") == "installed"
        t = self.trust.get(aid) or self.verify_trust(aid)
        out = {"artifact":aid,"status":"approved" if installed and t["verified"] and p["decision"]=="allow" else "denied","installed":installed,"policy":p,"trust":t}
        self.approvals[aid] = out; self.receipt("execution_approval", aid, out); return out

    def promote(self, aid):
        out = {"artifact":aid,"lane":"promotion","status":"promoted"}
        self.promotions[aid] = out; self.artifacts[aid]["status"] = "promoted"; self.receipt("promotion", aid, out); return out

    def quarantine_lane(self, aid, reason):
        out = {"artifact":aid,"lane":"quarantine","reason":reason,"status":"quarantined"}
        self.quarantine[aid] = out; self.artifacts[aid]["status"] = "quarantined"; self.receipt("quarantine", aid, out); return out

    def rollback(self, aid, reason):
        out = {"artifact":aid,"lane":"rollback","reason":reason,"status":"rolled_back"}
        self.rollbacks[aid] = out; self.artifacts[aid]["status"] = "rolled_back"; self.receipt("rollback", aid, out); return out

    def run(self, aid):
        rid = "pipeline:" + digest({"artifact":aid,"n":len(self.runs)})[:16]
        risk = self.score(aid); trust = self.verify_trust(aid); inst = self.install(aid); appr = self.approve_execution(aid)
        if risk["score"] >= 80 or not trust["verified"]:
            final = self.quarantine_lane(aid, "risk_or_trust_failure")
        elif inst["status"] == "installed" and appr["status"] == "approved":
            final = self.promote(aid)
        else:
            final = self.rollback(aid, "install_or_execution_denied")
        rec = {"id":rid,"artifact":aid,"risk":risk,"trust":trust,"install":inst,"approval":appr,"final":final,"status":final["status"]}
        self.runs[rid] = rec; self.receipt("pipeline_run", rid, rec); return rec

    def status(self):
        return {"artifacts":len(self.artifacts),"pipeline_runs":len(self.runs),"policy_gates":len(self.gates),"trust_checks":len(self.trust),"install_records":len(self.installs),"execution_approvals":len(self.approvals),"risk_scores":len(self.risks),"quarantined":len(self.quarantine),"promoted":len(self.promotions),"rolled_back":len(self.rollbacks),"receipts":len(self.receipts),"ledger":self.verify_ledger()}

    def dashboard(self):
        return {"version":"2.5.0","status":self.status(),"artifacts":self.artifacts,"pipeline_runs":self.runs,"policy_gates":self.gates,"trust_checks":self.trust,"install_records":self.installs,"execution_approvals":self.approvals,"risk_scores":self.risks,"quarantine":self.quarantine,"promotions":self.promotions,"rollbacks":self.rollbacks,"receipts":self.receipts}

    def export(self, out):
        out = Path(out)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for name, obj in {"pipeline_dashboard.json":self.dashboard(),"artifacts.json":self.artifacts,"pipeline_runs.json":self.runs,"policy_gates.json":self.gates,"trust_checks.json":self.trust,"install_records.json":self.installs,"execution_approvals.json":self.approvals,"risk_scores.json":self.risks,"quarantine.json":self.quarantine,"promotions.json":self.promotions,"rollbacks.json":self.rollbacks,"receipts.json":self.receipts,"ledger.json":self.ledger}.items():
                z.writestr(name, json.dumps(obj, indent=2, default=str))
            for p in sorted(self.receipts_dir.glob("*.json")):
                z.write(p, arcname="receipts/"+p.name)
        return {"bundle":str(out), "exists":out.exists()}

def seed_demo(td):
    p = Pipeline(Path(td)/"receipts")
    good = p.intake("operator-dashboard","1.0.0","trusted-root","dashboard api database",{"network":"required"})
    bad = p.intake("experimental-rootkit","0.1.0","unknown","bad artifact",{"privileged":True,"experimental":True})
    good_run = p.run(good["artifact"])
    bad_run = p.run(bad["artifact"])
    bundle = p.export(Path(td)/"policy_artifact_pipeline_bundle.zip")
    return {"good":good,"bad":bad,"good_run":good_run,"bad_run":bad_run,"status":p.status(),"bundle":bundle}
