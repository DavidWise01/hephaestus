
import json, hashlib, zipfile
from pathlib import Path

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()

class OperatorConsole:
    def __init__(self, state_dir="console_state"):
        self.state_dir = Path(state_dir); self.state_dir.mkdir(parents=True, exist_ok=True)
        self.nodes = {}; self.services = {}; self.artifacts = {}; self.deployments = {}
        self.state = {}; self.commands = []; self.events = []; self.health_timeline = []
        self.audit = []; self.ledger = []

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
        event = {"id":"event:"+digest({"k":kind,"s":subject,"n":len(self.events)})[:16], "kind":kind, "subject":subject, "payload":payload}
        self.events.append(event)
        self.audit.append({"action":kind, "subject":subject, "status":"recorded"})
        self.receipt("event", event["id"], event)
        return event

    def add_node(self, name):
        nid = "node:" + digest(name)[:16]
        self.nodes[nid] = {"id":nid, "name":name, "status":"online", "health":"ok"}
        self.emit("node.added", nid, self.nodes[nid])
        return {"node":nid}

    def add_service(self, name, node):
        sid = "service:" + digest({"name":name, "node":node})[:16]
        self.services[sid] = {"id":sid, "name":name, "node":node, "status":"running", "health":"ok"}
        self.emit("service.added", sid, self.services[sid])
        return {"service":sid}

    def add_artifact(self, name, kind):
        aid = "artifact:" + digest({"name":name, "kind":kind})[:16]
        self.artifacts[aid] = {"id":aid, "name":name, "kind":kind, "status":"registered"}
        self.emit("artifact.added", aid, self.artifacts[aid])
        return {"artifact":aid}

    def stop_service(self, sid):
        if sid in self.services:
            self.services[sid]["status"] = "stopped"; self.services[sid]["health"] = "failed"
            return {"status":"stopped", "service":sid}
        return {"status":"missing", "service":sid}

    def start_service(self, sid):
        if sid in self.services:
            self.services[sid]["status"] = "running"; self.services[sid]["health"] = "ok"
            return {"status":"running", "service":sid}
        return {"status":"missing", "service":sid}

    def repair(self, target):
        if target in self.nodes:
            self.nodes[target]["status"]="online"; self.nodes[target]["health"]="ok"
        if target in self.services:
            self.services[target]["status"]="running"; self.services[target]["health"]="ok"
        return {"status":"repaired", "target":target}

    def deploy(self, artifact, target):
        did = "deployment:" + digest({"artifact":artifact, "target":target})[:16]
        self.deployments[did] = {"id":did, "artifact":artifact, "target":target, "status":"deployed"}
        return {"status":"deployed", "deployment":did}

    def set_state(self, key, value):
        obj = {"key":key, "value":value, "version":self.state.get(key,{}).get("version",0)+1, "hash":digest(value)}
        self.state[key] = obj
        (self.state_dir/(key.replace(":","_")+".json")).write_text(json.dumps(obj, indent=2))
        return {"status":"state_set", "key":key}

    def route_command(self, command, target=None, payload=None):
        cid = "cmd:" + digest({"command":command, "target":target, "payload":payload, "n":len(self.commands)})[:16]
        payload = payload or {}
        if command == "repair":
            result = self.repair(target)
        elif command == "deploy":
            result = self.deploy(payload.get("artifact"), payload.get("target"))
        elif command == "set_state":
            result = self.set_state(payload.get("key"), payload.get("value"))
        elif command == "stop_service":
            result = self.stop_service(target)
        elif command == "start_service":
            result = self.start_service(target)
        elif command == "health":
            result = self.health()
        else:
            result = {"status":"unsupported"}
        record = {"id":cid, "command":command, "target":target, "payload":payload, "result":result}
        self.commands.append(record)
        self.emit("command.executed", cid, record)
        return result

    def health(self):
        h = {
            "nodes":len(self.nodes),
            "healthy_nodes":len([n for n in self.nodes.values() if n["health"]=="ok"]),
            "services":len(self.services),
            "healthy_services":len([s for s in self.services.values() if s["health"]=="ok"]),
            "artifacts":len(self.artifacts),
            "deployments":len(self.deployments),
            "state_objects":len(self.state),
            "events":len(self.events),
            "commands":len(self.commands),
            "audit_entries":len(self.audit),
            "ledger":self.verify_ledger()
        }
        self.health_timeline.append(h)
        return h

    def dashboard(self):
        return {"version":"1.7.0","health":self.health(),"nodes":list(self.nodes.values()),"services":list(self.services.values()),"artifacts":list(self.artifacts.values()),"deployments":list(self.deployments.values()),"state":self.state,"commands":self.commands,"events":self.events,"health_timeline":self.health_timeline,"audit":self.audit}

    def export(self, out):
        out = Path(out)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("operator_console_dashboard.json", json.dumps(self.dashboard(), indent=2, default=str))
            z.writestr("nodes.json", json.dumps(list(self.nodes.values()), indent=2))
            z.writestr("services.json", json.dumps(list(self.services.values()), indent=2))
            z.writestr("artifacts.json", json.dumps(list(self.artifacts.values()), indent=2))
            z.writestr("deployments.json", json.dumps(list(self.deployments.values()), indent=2))
            z.writestr("commands.json", json.dumps(self.commands, indent=2))
            z.writestr("events.json", json.dumps(self.events, indent=2))
            z.writestr("health_timeline.json", json.dumps(self.health_timeline, indent=2, default=str))
            z.writestr("audit.json", json.dumps(self.audit, indent=2))
            z.writestr("ledger.json", json.dumps(self.ledger, indent=2))
            for p in sorted(self.state_dir.glob("*.json")):
                z.write(p, arcname="console_state/"+p.name)
        return {"bundle":str(out), "exists":out.exists()}

def seed_demo(td):
    c = OperatorConsole(Path(td)/"console_state")
    n1 = c.add_node("north"); n2 = c.add_node("south")
    s1 = c.add_service("api", n1["node"])
    s2 = c.add_service("dashboard", n1["node"])
    s3 = c.add_service("worker", n2["node"])
    art = c.add_artifact("operator-platform", "generated_app")
    c.route_command("set_state", payload={"key":"console:mode", "value":{"mode":"active","version":"1.7.0"}})
    c.route_command("stop_service", target=s3["service"])
    c.route_command("repair", target=s3["service"])
    dep = c.route_command("deploy", payload={"artifact":art["artifact"], "target":n1["node"]})
    c.route_command("health")
    health = c.health()  # FIX 2026-06 (AVAN audit): read AFTER the record appends - the health command now counts itself (off-by-one)
    bundle = c.export(Path(td)/"operator_console_bundle.zip")
    return {"nodes":[n1,n2], "services":[s1,s2,s3], "artifact":art, "deployment":dep, "health":health, "bundle":bundle}
