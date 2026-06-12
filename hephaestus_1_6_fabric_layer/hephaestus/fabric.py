
import json, hashlib, zipfile
from pathlib import Path

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()

class FabricLayer:
    def __init__(self, state_dir="fabric_state", deployment_dir="deployments"):
        self.state_dir = Path(state_dir); self.state_dir.mkdir(parents=True, exist_ok=True)
        self.deployment_dir = Path(deployment_dir); self.deployment_dir.mkdir(parents=True, exist_ok=True)
        self.nodes = {}; self.runtimes = {}; self.services = {}; self.routes = {}
        self.state = {}; self.policies = {}; self.artifacts = {}; self.deployments = {}
        self.events = []; self.ledger = []

    def receipt(self, kind, subject, payload):
        prev = self.ledger[-1]["entry_hash"] if self.ledger else "GENESIS"
        ph = digest(payload)
        eh = digest({"kind":kind, "subject":subject, "payload_hash":ph, "prev_hash":prev})
        self.ledger.append({"kind":kind, "subject":subject, "payload_hash":ph, "prev_hash":prev, "entry_hash":eh})

    def verify_ledger(self):
        prev = "GENESIS"
        for i, row in enumerate(self.ledger, start=1):
            exp = digest({"kind":row["kind"], "subject":row["subject"], "payload_hash":row["payload_hash"], "prev_hash":prev})
            if row["prev_hash"] != prev or row["entry_hash"] != exp:
                return {"ok":False, "seq":i}
            prev = row["entry_hash"]
        return {"ok":True, "entries":len(self.ledger), "head":prev}

    def emit(self, kind, subject, payload):
        eid = "event:" + digest({"kind":kind, "subject":subject, "payload":payload, "n":len(self.events)})[:16]
        event = {"id":eid, "kind":kind, "subject":subject, "payload":payload}
        self.events.append(event)
        self.receipt("event", eid, event)
        return event

    def register_node(self, name, zone):
        nid = "node:" + digest({"name":name, "zone":zone})[:16]
        self.nodes[nid] = {"id":nid, "name":name, "zone":zone, "status":"online", "health":"ok"}
        self.emit("node.registered", nid, self.nodes[nid])
        return {"node":nid}

    def bind_runtime(self, node, name):
        rid = "runtime:" + digest({"node":node, "name":name})[:16]
        self.runtimes[rid] = {"id":rid, "node":node, "name":name, "status":"active", "health":"ok"}
        self.emit("runtime.bound", rid, self.runtimes[rid])
        return {"runtime":rid}

    def bind_service(self, runtime, name, kind, endpoint):
        sid = "service:" + digest({"runtime":runtime, "name":name})[:16]
        self.services[sid] = {"id":sid, "runtime":runtime, "name":name, "kind":kind, "endpoint":endpoint, "status":"running", "health":"ok"}
        self.emit("service.bound", sid, self.services[sid])
        return {"service":sid}

    def add_route(self, path, service):
        rid = "route:" + digest({"path":path, "service":service})[:16]
        self.routes[rid] = {"id":rid, "path":path, "service":service, "status":"active"}
        self.emit("route.added", rid, self.routes[rid])
        return {"route":rid}

    def put_state(self, key, value):
        obj = {"key":key, "value":value, "version":self.state.get(key,{}).get("version",0)+1, "hash":digest(value)}
        self.state[key] = obj
        (self.state_dir/(key.replace(":","_")+".json")).write_text(json.dumps(obj, indent=2))
        self.emit("state.updated", key, obj)
        return obj

    def add_policy(self, name, target_kind, action):
        pid = "policy:" + digest({"name":name, "target":target_kind, "action":action})[:16]
        self.policies[pid] = {"id":pid, "name":name, "target_kind":target_kind, "action":action, "status":"active"}
        self.emit("policy.added", pid, self.policies[pid])
        return {"policy":pid}

    def register_artifact(self, name, kind, content):
        aid = "artifact:" + digest({"name":name, "kind":kind, "content":content})[:16]
        self.artifacts[aid] = {"id":aid, "name":name, "kind":kind, "status":"registered", "hash":hashlib.sha256(content.encode()).hexdigest()}
        self.emit("artifact.registered", aid, self.artifacts[aid])
        return {"artifact":aid}

    def deploy(self, artifact, runtime):
        did = "deployment:" + digest({"artifact":artifact, "runtime":runtime})[:16]
        self.deployments[did] = {"id":did, "artifact":artifact, "runtime":runtime, "status":"deployed"}
        (self.deployment_dir/(did.replace(":","_")+".json")).write_text(json.dumps(self.deployments[did], indent=2))
        self.emit("artifact.deployed", did, self.deployments[did])
        return {"deployment":did}

    def fail(self, target):
        for collection in [self.nodes, self.runtimes, self.services]:
            if target in collection:
                collection[target]["status"] = "failed"
                collection[target]["health"] = "failed"
        self.emit("failure.detected", target, {"target":target})
        return {"target":target, "status":"failed"}

    def heal(self, target):
        if target in self.nodes:
            self.nodes[target]["status"] = "online"; self.nodes[target]["health"] = "ok"
        if target in self.runtimes:
            self.runtimes[target]["status"] = "active"; self.runtimes[target]["health"] = "ok"
        if target in self.services:
            self.services[target]["status"] = "running"; self.services[target]["health"] = "ok"
        self.emit("healing.applied", target, {"target":target, "status":"ok"})
        return {"target":target, "status":"healed"}

    def health(self):
        return {
            "nodes":len(self.nodes),
            "healthy_nodes":len([x for x in self.nodes.values() if x["health"]=="ok"]),
            "runtimes":len(self.runtimes),
            "healthy_runtimes":len([x for x in self.runtimes.values() if x["health"]=="ok"]),
            "services":len(self.services),
            "healthy_services":len([x for x in self.services.values() if x["health"]=="ok"]),
            "routes":len(self.routes),
            "state_objects":len(self.state),
            "healing_policies":len(self.policies),
            "artifacts":len(self.artifacts),
            "deployments":len(self.deployments),
            "events":len(self.events),
            "ledger":self.verify_ledger()
        }

    def dashboard(self):
        return {"version":"1.6.0","health":self.health(),"nodes":list(self.nodes.values()),"runtimes":list(self.runtimes.values()),"services":list(self.services.values()),"routes":list(self.routes.values()),"state":self.state,"policies":list(self.policies.values()),"artifacts":list(self.artifacts.values()),"deployments":list(self.deployments.values()),"events":self.events}

    def export(self, out):
        out = Path(out)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("fabric_dashboard.json", json.dumps(self.dashboard(), indent=2, default=str))
            z.writestr("global_health.json", json.dumps(self.health(), indent=2, default=str))
            z.writestr("events.json", json.dumps(self.events, indent=2, default=str))
            z.writestr("ledger.json", json.dumps(self.ledger, indent=2, default=str))
            for name, obj in [("nodes",self.nodes),("runtimes",self.runtimes),("services",self.services),("routes",self.routes),("state",self.state),("policies",self.policies),("artifacts",self.artifacts),("deployments",self.deployments)]:
                z.writestr(f"{name}.json", json.dumps(obj, indent=2, default=str))
            for p in sorted(self.state_dir.glob("*.json")):
                z.write(p, arcname="fabric_state/"+p.name)
            for p in sorted(self.deployment_dir.glob("*.json")):
                z.write(p, arcname="deployments/"+p.name)
        return {"bundle":str(out), "exists":out.exists()}

def seed_demo(td):
    f = FabricLayer(Path(td)/"fabric_state", Path(td)/"deployments")
    n1 = f.register_node("north","zone-a"); n2 = f.register_node("south","zone-b")
    r1 = f.bind_runtime(n1["node"],"runtime-north"); r2 = f.bind_runtime(n2["node"],"runtime-south")
    s1 = f.bind_service(r1["runtime"],"api","service","http://127.0.0.1:8100")
    s2 = f.bind_service(r1["runtime"],"dashboard","ui","http://127.0.0.1:8100/dashboard")
    s3 = f.bind_service(r2["runtime"],"worker","worker","internal://worker")
    f.add_route("/api/status", s1["service"]); f.add_route("/dashboard", s2["service"])
    f.put_state("config:runtime", {"mode":"active","version":"1.6.0"})
    f.put_state("mesh:policy", {"failover":"enabled","healing":"enabled"})
    f.add_policy("restart-stopped-service","service","restart")
    art = f.register_artifact("operator-platform","generated_app","dashboard api database workflow reports security")
    dep = f.deploy(art["artifact"], r1["runtime"])
    f.fail(s3["service"]); heal = f.heal(s3["service"])
    bundle = f.export(Path(td)/"fabric_bundle.zip")
    return {"nodes":[n1,n2],"runtimes":[r1,r2],"services":[s1,s2,s3],"artifact":art,"deployment":dep,"healing":heal,"health":f.health(),"bundle":bundle}
