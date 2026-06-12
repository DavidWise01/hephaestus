
import json, hashlib, zipfile
from pathlib import Path

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()

class SelfHealingRuntime:
    def __init__(self, checkpoints="checkpoints"):
        self.checkpoints = Path(checkpoints)
        self.checkpoints.mkdir(parents=True, exist_ok=True)
        self.nodes = {}
        self.services = {}
        self.replications = []
        self.failures = []
        self.repairs = []
        self.checkpoint_log = []
        self.healing_journal = []
        self.ledger = []

    def receipt(self, kind, subject, payload):
        prev = self.ledger[-1]["entry_hash"] if self.ledger else "GENESIS"
        ph = digest(payload)
        eh = digest({"kind": kind, "subject": subject, "payload_hash": ph, "prev_hash": prev})
        self.ledger.append({"kind": kind, "subject": subject, "payload_hash": ph, "prev_hash": prev, "entry_hash": eh})

    def verify_ledger(self):
        prev = "GENESIS"
        for i, r in enumerate(self.ledger, start=1):
            exp = digest({"kind": r["kind"], "subject": r["subject"], "payload_hash": r["payload_hash"], "prev_hash": prev})
            if r["prev_hash"] != prev or r["entry_hash"] != exp:
                return {"ok": False, "seq": i}
            prev = r["entry_hash"]
        return {"ok": True, "entries": len(self.ledger), "head": prev}

    def add_node(self, name, role="follower"):
        nid = "node:" + digest({"name": name})[:16]
        self.nodes[nid] = {"id": nid, "name": name, "role": role, "status": "online", "health": "ok"}
        self.receipt("node_added", nid, self.nodes[nid])
        return {"node": nid}

    def add_service(self, name, node):
        sid = "service:" + digest({"name": name, "node": node})[:16]
        self.services[sid] = {"id": sid, "name": name, "node": node, "status": "running", "health": "ok", "restart_count": 0}
        self.receipt("service_added", sid, self.services[sid])
        return {"service": sid}

    def checkpoint(self, label="checkpoint"):
        data = {"nodes": self.nodes, "services": self.services, "replications": self.replications}
        h = digest(data)
        cid = "checkpoint:" + h[:16]
        path = self.checkpoints / (cid.replace(":", "_") + ".json")
        path.write_text(json.dumps({"label": label, "hash": h, "data": data}, indent=2))
        item = {"id": cid, "label": label, "path": str(path), "hash": h}
        self.checkpoint_log.append(item)
        self.receipt("checkpoint", cid, item)
        return item

    def replicate(self, src, dst, key, value):
        event = {"src": src, "dst": dst, "key": key, "hash": digest(value), "status": "complete"}
        self.replications.append(event)
        self.receipt("replicated", key, event)
        return event

    def inject_failure(self, target, reason):
        if target in self.nodes:
            self.nodes[target]["status"] = "offline"
            self.nodes[target]["health"] = "failed"
        if target in self.services:
            self.services[target]["status"] = "stopped"
            self.services[target]["health"] = "failed"
        item = {"id": "failure:" + digest({"target": target, "reason": reason, "n": len(self.failures)})[:16], "target": target, "reason": reason, "status": "open"}
        self.failures.append(item)
        self.receipt("failure_detected", item["id"], item)
        return item

    def detect_failures(self):
        found = []
        for n in self.nodes.values():
            if n["health"] != "ok":
                found.append({"target": n["id"], "kind": "node", "reason": n["health"]})
        for s in self.services.values():
            if s["health"] != "ok":
                found.append({"target": s["id"], "kind": "service", "reason": s["health"]})
        self.receipt("failure_scan", "scan", {"found": len(found)})
        return found

    def plan_repair(self, target):
        kind = "node" if target in self.nodes else "service" if target in self.services else "unknown"
        steps = ["restore node", "restore services", "rejoin cluster"] if kind == "node" else ["restart service", "health check"]
        plan = {"id": "repair:" + digest({"target": target, "kind": kind})[:16], "target": target, "kind": kind, "steps": steps, "status": "planned"}
        self.repairs.append(plan)
        self.receipt("repair_planned", plan["id"], plan)
        return plan

    def execute_repair(self, repair_id):
        plan = next(r for r in self.repairs if r["id"] == repair_id)
        target = plan["target"]
        if target in self.nodes:
            self.nodes[target]["status"] = "online"
            self.nodes[target]["health"] = "ok"
            for s in self.services.values():
                if s["node"] == target:
                    s["status"] = "running"
                    s["health"] = "ok"
        if target in self.services:
            self.services[target]["status"] = "running"
            self.services[target]["health"] = "ok"
            self.services[target]["restart_count"] += 1
        plan["status"] = "complete"
        event = {"repair": repair_id, "target": target, "status": "complete"}
        self.healing_journal.append(event)
        self.receipt("repair_complete", repair_id, event)
        return event

    def leader_recovery(self):
        leaders = [n for n in self.nodes.values() if n["role"] == "leader" and n["status"] == "online"]
        if leaders:
            return {"status": "leader_ok", "leader": leaders[0]["id"]}
        online = sorted([n for n in self.nodes.values() if n["status"] == "online"], key=lambda x: x["id"])
        if not online:
            return {"status": "no_online_nodes", "leader": None}
        for n in self.nodes.values():
            n["role"] = "follower"
        online[0]["role"] = "leader"
        event = {"status": "leader_recovered", "leader": online[0]["id"]}
        self.healing_journal.append(event)
        self.receipt("leader_recovered", online[0]["id"], event)
        return event

    def repair_replication(self):
        repaired = 0
        for r in self.replications:
            if r["status"] != "complete":
                r["status"] = "complete"
                repaired += 1
        event = {"status": "replication_repaired", "count": repaired}
        self.healing_journal.append(event)
        self.receipt("replication_repair", "replication", event)
        return event

    def reconcile_state(self):
        event = {"status": "state_reconciled", "nodes": len(self.nodes), "services": len(self.services)}
        self.healing_journal.append(event)
        self.receipt("state_reconciled", "cluster", event)
        return event

    def heal_all(self):
        found = self.detect_failures()
        repairs = []
        for f in found:
            plan = self.plan_repair(f["target"])
            repairs.append(self.execute_repair(plan["id"]))
        return {
            "found": found,
            "repairs": repairs,
            "leader": self.leader_recovery(),
            "replication": self.repair_replication(),
            "reconciliation": self.reconcile_state()
        }

    def health(self):
        return {
            "nodes": len(self.nodes),
            "online_nodes": len([n for n in self.nodes.values() if n["status"] == "online"]),
            "services": len(self.services),
            "running_services": len([s for s in self.services.values() if s["status"] == "running"]),
            "failures": len(self.failures),
            "repairs": len(self.repairs),
            "healing_events": len(self.healing_journal),
            "checkpoints": len(self.checkpoint_log),
            "ledger": self.verify_ledger()
        }

    def dashboard(self):
        return {"version": "1.5.0", "health": self.health(), "nodes": list(self.nodes.values()), "services": list(self.services.values()), "failures": self.failures, "repairs": self.repairs, "replications": self.replications, "checkpoints": self.checkpoint_log, "healing_journal": self.healing_journal}

    def export(self, out):
        out = Path(out)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("self_healing_dashboard.json", json.dumps(self.dashboard(), indent=2))
            z.writestr("nodes.json", json.dumps(list(self.nodes.values()), indent=2))
            z.writestr("services.json", json.dumps(list(self.services.values()), indent=2))
            z.writestr("failures.json", json.dumps(self.failures, indent=2))
            z.writestr("repairs.json", json.dumps(self.repairs, indent=2))
            z.writestr("healing_journal.json", json.dumps(self.healing_journal, indent=2))
            z.writestr("ledger.json", json.dumps(self.ledger, indent=2))
            for p in sorted(self.checkpoints.glob("*.json")):
                z.write(p, arcname="checkpoints/" + p.name)
        return {"bundle": str(out), "exists": out.exists()}

def seed_demo(td):
    rt = SelfHealingRuntime(Path(td) / "checkpoints")
    n1 = rt.add_node("north", "leader")
    n2 = rt.add_node("south")
    n3 = rt.add_node("east")
    s1 = rt.add_service("api", n1["node"])
    s2 = rt.add_service("dashboard", n2["node"])
    s3 = rt.add_service("worker", n3["node"])
    rt.replicate(n1["node"], n2["node"], "config:runtime", {"mode": "active"})
    rt.replicate(n1["node"], n3["node"], "config:runtime", {"mode": "active"})
    checkpoint = rt.checkpoint("before_failure")
    rt.inject_failure(n1["node"], "leader_node_timeout")
    rt.inject_failure(s3["service"], "worker_stopped")
    healing = rt.heal_all()
    bundle = rt.export(Path(td) / "self_healing_bundle.zip")
    return {"nodes":[n1,n2,n3],"services":[s1,s2,s3],"checkpoint":checkpoint,"healing":healing,"health":rt.health(),"bundle":bundle}
