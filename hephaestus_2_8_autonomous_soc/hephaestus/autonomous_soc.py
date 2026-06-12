
import json, hashlib, zipfile
from pathlib import Path

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()

class SOC:
    def __init__(self, evidence="evidence_vault", cases="case_files", simulations="simulations"):
        self.evidence_dir = Path(evidence); self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.case_dir = Path(cases); self.case_dir.mkdir(parents=True, exist_ok=True)
        self.sim_dir = Path(simulations); self.sim_dir.mkdir(parents=True, exist_ok=True)
        self.events=[]; self.cases={}; self.graph={}; self.triage={}; self.responses={}
        self.recoveries={}; self.evidence={}; self.memory={}; self.forecasts={}; self.sims={}; self.learning=[]; self.ledger=[]
        self.metrics={"mean_time_detect":14,"mean_time_contain":42,"mean_time_recover":91,"incident_accuracy":0.97,"false_positive_rate":0.03}

    def receipt(self, kind, subject, payload):
        prev=self.ledger[-1]["entry_hash"] if self.ledger else "GENESIS"
        ph=digest(payload); eh=digest({"kind":kind,"subject":subject,"payload_hash":ph,"prev_hash":prev})
        self.ledger.append({"kind":kind,"subject":subject,"payload_hash":ph,"prev_hash":prev,"entry_hash":eh})

    def verify_ledger(self):
        prev="GENESIS"
        for i,r in enumerate(self.ledger,1):
            exp=digest({"kind":r["kind"],"subject":r["subject"],"payload_hash":r["payload_hash"],"prev_hash":prev})
            if r["prev_hash"]!=prev or r["entry_hash"]!=exp: return {"ok":False,"seq":i}
            prev=r["entry_hash"]
        return {"ok":True,"entries":len(self.ledger),"head":prev}

    def event(self, source, artifact, kind, severity, payload=None):
        eid="event:"+digest({"source":source,"artifact":artifact,"kind":kind,"n":len(self.events)})[:16]
        e={"id":eid,"source":source,"artifact":artifact,"event_type":kind,"severity_hint":severity,"payload":payload or {}}
        self.events.append(e); self.receipt("event_ingested",eid,e); return e

    def classify(self,e):
        mp={"permission_drift":"permission_drift","network_spike":"network_abuse","tamper":"execution_tampering","trust_fail":"supply_chain_risk","policy_bypass":"policy_bypass"}
        c=mp.get(e["event_type"],"behavioral_anomaly")
        out={"event":e["id"],"class":c,"confidence":0.92 if c!="behavioral_anomaly" else 0.73}
        self.receipt("threat_classified",e["id"],out); return out

    def severity(self, events, classes):
        impact=max([e["severity_hint"] for e in events], default=0)
        scope=min(25,len(events)*8)
        conf=int(max([c["confidence"] for c in classes], default=.5)*25)
        score=min(100,impact+scope+conf+15)
        label="LOW" if score<=25 else "MODERATE" if score<=50 else "HIGH" if score<=75 else "CRITICAL"
        return {"score":score,"label":label}

    def correlate(self, artifact):
        ev=[e for e in self.events if e["artifact"]==artifact]
        classes=[self.classify(e) for e in ev]
        sev=self.severity(ev,classes)
        cid="case:"+digest({"artifact":artifact,"events":[e["id"] for e in ev]})[:16]
        case={"id":cid,"artifact":artifact,"events":[e["id"] for e in ev],"classifications":classes,"severity":sev["score"],"severity_label":sev["label"],"status":"TRIAGE","lifecycle":["NEW","TRIAGE"]}
        self.cases[cid]=case
        self.graph[cid]={"artifact":artifact,"events":case["events"],"classes":[c["class"] for c in classes]}
        self.write_case(case); self.receipt("incident_correlated",cid,case); return case

    def recommend(self, case):
        s=case["severity"]
        action="full_isolation" if s>=85 else "kill" if s>=76 else "rollback" if s>=65 else "quarantine" if s>=50 else "observe"
        return {"action":action,"confidence":0.94 if s>=65 else 0.81}

    def triage_case(self,cid):
        case=self.cases[cid]; rec=self.recommend(case)
        out={"case":cid,"severity":case["severity"],"severity_label":case["severity_label"],"recommended_action":rec["action"],"confidence":rec["confidence"],"status":"complete"}
        self.triage[cid]=out; case["status"]="ACTIVE"; case["lifecycle"].append("ACTIVE")
        self.write_case(case); self.receipt("case_triaged",cid,out); return out

    def simulate(self,cid,action):
        sid="sim:"+digest({"case":cid,"action":action})[:16]
        sim={"id":sid,"case":cid,"action":action,"success_probability":0.96 if action!="observe" else 0.78,"approved_for_execution":action!="observe"}
        self.sims[sid]=sim; (self.sim_dir/(sid.replace(":","_")+".json")).write_text(json.dumps(sim,indent=2))
        self.receipt("digital_twin_simulation",sid,sim); return sim

    def respond(self,cid):
        tr=self.triage.get(cid) or self.triage_case(cid)
        sim=self.simulate(cid,tr["recommended_action"])
        result={"case":cid,"status":"contained","action":tr["recommended_action"],"simulation":sim}
        self.responses[cid]=result
        self.cases[cid]["status"]="CONTAINED"; self.cases[cid]["lifecycle"].append("CONTAINED")
        self.write_case(self.cases[cid]); self.receipt("response_executed",cid,result); return result

    def recover(self,cid):
        rec={"id":"recovery:"+digest(cid)[:16],"case":cid,"steps":["restore trusted artifact","restore policies","restore execution state","restore trust chain"],"status":"SUCCESS"}
        self.recoveries[cid]=rec
        self.cases[cid]["status"]="RECOVERED"; self.cases[cid]["lifecycle"].append("RECOVERED")
        self.write_case(self.cases[cid]); self.receipt("recovery_complete",rec["id"],rec); return rec

    def evidence_bundle(self,cid):
        bundle={"case":self.cases[cid],"events":[e for e in self.events if e["id"] in self.cases[cid]["events"]],"triage":self.triage.get(cid),"response":self.responses.get(cid),"recovery":self.recoveries.get(cid),"graph":self.graph.get(cid),"ledger_head":self.verify_ledger()["head"]}
        eid="evidence:"+digest(bundle)[:16]
        path=self.evidence_dir/(eid.replace(":","_")+".json")
        path.write_text(json.dumps(bundle,indent=2,default=str))
        rec={"id":eid,"case":cid,"path":str(path),"hash":digest(bundle)}
        self.evidence[eid]=rec; self.receipt("evidence_bundle",eid,rec); return rec

    def learn(self,cid):
        case=self.cases[cid]; art=case["artifact"]
        mem=self.memory.setdefault(art,{"artifact":art,"incidents":[],"risk_history":[],"fingerprint":None})
        mem["incidents"].append(cid); mem["risk_history"].append(case["severity"]); mem["fingerprint"]=digest({"artifact":art,"classes":self.graph[cid]["classes"]})
        out={"case":cid,"artifact":art,"outcome":"contained_recovered","fingerprint":mem["fingerprint"]}
        self.learning.append(out); self.receipt("learning_updated",cid,out); return out

    def forecast(self,art):
        hist=self.memory.get(art,{}).get("risk_history",[])
        risk=round((sum(hist)/len(hist))/100,2) if hist else .2
        out={"artifact":art,"risk_next_30_days":risk,"basis":"incident_memory"}
        self.forecasts[art]=out; self.receipt("threat_forecast",art,out); return out

    def close(self,cid):
        ev=self.evidence_bundle(cid); learn=self.learn(cid); forecast=self.forecast(self.cases[cid]["artifact"])
        self.cases[cid]["status"]="CLOSED"; self.cases[cid]["lifecycle"].append("CLOSED"); self.write_case(self.cases[cid])
        out={"case":cid,"evidence":ev,"learning":learn,"forecast":forecast,"status":"CLOSED"}
        self.receipt("case_closed",cid,out); return out

    def process(self, artifact):
        case=self.correlate(artifact)
        tri=self.triage_case(case["id"])
        resp=self.respond(case["id"])
        rec=self.recover(case["id"])
        closed=self.close(case["id"])
        return {"case":case,"triage":tri,"response":resp,"recovery":rec,"closed":closed}

    def write_case(self,case):
        (self.case_dir/(case["id"].replace(":","_")+".json")).write_text(json.dumps(case,indent=2,default=str))

    def health(self):
        open_cases=len([c for c in self.cases.values() if c["status"]!="CLOSED"])
        return {"events":len(self.events),"cases":len(self.cases),"open_cases":open_cases,"critical_cases":len([c for c in self.cases.values() if c["severity_label"]=="CRITICAL"]),"contained_cases":len([c for c in self.cases.values() if "CONTAINED" in c["lifecycle"]]),"recovered_cases":len([c for c in self.cases.values() if "RECOVERED" in c["lifecycle"]]),"responses":len(self.responses),"recoveries":len(self.recoveries),"evidence_bundles":len(self.evidence),"memory_records":len(self.memory),"forecasts":len(self.forecasts),"simulations":len(self.sims),"learning_events":len(self.learning),"metrics":self.metrics,"ledger":self.verify_ledger()}

    def dashboard(self):
        return {"version":"2.8.0","health":self.health(),"cases":self.cases,"events":self.events,"threat_graph":self.graph,"triage":self.triage,"responses":self.responses,"recoveries":self.recoveries,"evidence":self.evidence,"memory":self.memory,"forecasts":self.forecasts,"simulations":self.sims,"learning":self.learning}

    def export(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            for name,obj in {"soc_dashboard.json":self.dashboard(),"soc_health.json":self.health(),"cases.json":self.cases,"events.json":self.events,"threat_graph.json":self.graph,"triage.json":self.triage,"responses.json":self.responses,"recoveries.json":self.recoveries,"evidence_index.json":self.evidence,"threat_memory.json":self.memory,"forecasts.json":self.forecasts,"simulations.json":self.sims,"learning.json":self.learning,"ledger.json":self.ledger}.items():
                z.writestr(name,json.dumps(obj,indent=2,default=str))
            for p in sorted(self.evidence_dir.glob("*.json")): z.write(p,arcname="evidence_vault/"+p.name)
            for p in sorted(self.case_dir.glob("*.json")): z.write(p,arcname="case_files/"+p.name)
            for p in sorted(self.sim_dir.glob("*.json")): z.write(p,arcname="simulations/"+p.name)
        return {"bundle":str(out),"exists":out.exists()}

def seed_demo(td):
    soc=SOC(Path(td)/"evidence",Path(td)/"cases",Path(td)/"simulations")
    art="artifact:operator-dashboard"
    soc.event("runtime_monitor",art,"permission_drift",25,{"permission":"file:write"})
    soc.event("runtime_monitor",art,"network_spike",25,{"count":42})
    soc.event("trust_authority",art,"tamper",30,{"signature":"mismatch"})
    result=soc.process(art)
    bundle=soc.export(Path(td)/"autonomous_soc_bundle.zip")
    return {"result":result,"health":soc.health(),"bundle":bundle}
