
import json, hashlib, zipfile
from pathlib import Path

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()

class AutonomousOrchestrator:
    def __init__(self, state_dir="orchestrator_state", plan_dir="plans"):
        self.state_dir = Path(state_dir); self.state_dir.mkdir(parents=True, exist_ok=True)
        self.plan_dir = Path(plan_dir); self.plan_dir.mkdir(parents=True, exist_ok=True)
        self.workloads = {}
        self.resources = {}
        self.deployments = {}
        self.healing_plans = {}
        self.lifecycle = {}
        self.events = []
        self.automations = []
        self.risk = {}
        self.execution_log = []
        self.ledger = []

    def receipt(self, kind, subject, payload):
        prev = self.ledger[-1]["entry_hash"] if self.ledger else "GENESIS"
        ph = digest(payload)
        eh = digest({"kind": kind, "subject": subject, "payload_hash": ph, "prev_hash": prev})
        self.ledger.append({"kind": kind, "subject": subject, "payload_hash": ph, "prev_hash": prev, "entry_hash": eh})

    def verify_ledger(self):
        prev = "GENESIS"
        for i, row in enumerate(self.ledger, start=1):
            exp = digest({"kind": row["kind"], "subject": row["subject"], "payload_hash": row["payload_hash"], "prev_hash": prev})
            if row["prev_hash"] != prev or row["entry_hash"] != exp:
                return {"ok": False, "seq": i}
            prev = row["entry_hash"]
        return {"ok": True, "entries": len(self.ledger), "head": prev}

    def add_resource(self, node, cpu, memory, storage, network):
        rid = "resource:" + digest({"node": node})[:16]
        self.resources[rid] = {"id": rid, "node": node, "cpu": cpu, "memory": memory, "storage": storage, "network": network, "status": "available"}
        self.receipt("resource_added", rid, self.resources[rid])
        return {"resource": rid}

    def add_workload(self, name, kind, priority=5, cpu=1, memory=1):
        wid = "workload:" + digest({"name": name, "kind": kind, "priority": priority})[:16]
        self.workloads[wid] = {"id": wid, "name": name, "kind": kind, "priority": priority, "cpu": cpu, "memory": memory, "status": "queued"}
        self.lifecycle[wid] = ["created", "queued"]
        self.receipt("workload_added", wid, self.workloads[wid])
        return {"workload": wid}

    def policy_check(self, action, target, risk_score):
        allowed = risk_score < 80
        result = {"action": action, "target": target, "risk_score": risk_score, "allowed": allowed, "decision": "allow" if allowed else "hold"}
        self.receipt("policy_check", target, result)
        return result

    def allocate(self, workload):
        w = self.workloads[workload]
        candidates = [r for r in self.resources.values() if r["status"] == "available" and r["cpu"] >= w["cpu"] and r["memory"] >= w["memory"]]
        if not candidates:
            return {"status": "no_capacity", "workload": workload}
        best = sorted(candidates, key=lambda r: (r["cpu"] + r["memory"]), reverse=True)[0]
        best["cpu"] -= w["cpu"]; best["memory"] -= w["memory"]
        plan = {"workload": workload, "resource": best["id"], "node": best["node"], "status": "allocated"}
        self.receipt("resource_allocated", workload, plan)
        return plan

    def schedule(self):
        queued = sorted([w for w in self.workloads.values() if w["status"] == "queued"], key=lambda w: w["priority"], reverse=True)
        plans = []
        for w in queued:
            risk = self.score_risk(w["id"])
            gate = self.policy_check("schedule", w["id"], risk["score"])
            if not gate["allowed"]:
                w["status"] = "held"
                plans.append({"workload": w["id"], "status": "held", "risk": risk})
                continue
            allocation = self.allocate(w["id"])
            if allocation["status"] == "allocated":
                w["status"] = "scheduled"
                self.lifecycle[w["id"]].append("scheduled")
            plans.append({"workload": w["id"], "allocation": allocation, "risk": risk})
        self.receipt("schedule_complete", "scheduler", {"plans": len(plans)})
        return plans

    def deployment_plan(self, workload, strategy="rolling"):
        did = "deployment:" + digest({"workload": workload, "strategy": strategy})[:16]
        plan = {"id": did, "workload": workload, "strategy": strategy, "steps": ["prepare", "deploy", "verify", "promote"], "status": "planned"}
        self.deployments[did] = plan
        path = self.plan_dir / (did.replace(":", "_") + ".json")
        path.write_text(json.dumps(plan, indent=2))
        self.receipt("deployment_planned", did, plan)
        return {"deployment": did}

    def execute_deployment(self, deployment):
        d = self.deployments[deployment]
        risk = self.score_risk(d["workload"])
        gate = self.policy_check("deploy", deployment, risk["score"])
        if not gate["allowed"]:
            d["status"] = "held"
            return {"deployment": deployment, "status": "held"}
        d["status"] = "deployed"
        self.lifecycle[d["workload"]].append("deployed")
        event = {"deployment": deployment, "status": "deployed"}
        self.execution_log.append(event)
        self.receipt("deployment_executed", deployment, event)
        return event

    def healing_plan(self, target, reason):
        hid = "healing:" + digest({"target": target, "reason": reason})[:16]
        plan = {"id": hid, "target": target, "reason": reason, "decision": "repair", "steps": ["isolate", "repair", "verify", "resume"], "status": "planned"}
        self.healing_plans[hid] = plan
        self.receipt("healing_planned", hid, plan)
        return {"healing": hid}

    def execute_healing(self, healing):
        h = self.healing_plans[healing]
        risk = self.score_risk(h["target"])
        gate = self.policy_check("heal", healing, risk["score"])
        if not gate["allowed"]:
            h["status"] = "held"
            return {"healing": healing, "status": "held"}
        h["status"] = "complete"
        event = {"healing": healing, "target": h["target"], "status": "complete"}
        self.execution_log.append(event)
        self.receipt("healing_executed", healing, event)
        return event

    def emit_event(self, kind, target, payload=None):
        eid = "event:" + digest({"kind": kind, "target": target, "n": len(self.events)})[:16]
        event = {"id": eid, "kind": kind, "target": target, "payload": payload or {}}
        self.events.append(event)
        self.receipt("event", eid, event)
        return event

    def automate_events(self):
        actions = []
        for event in self.events:
            if event["kind"] == "service.failed":
                plan = self.healing_plan(event["target"], "service_failed")
                actions.append(self.execute_healing(plan["healing"]))
            if event["kind"] == "artifact.ready":
                plan = self.deployment_plan(event["target"], "rolling")
                actions.append(self.execute_deployment(plan["deployment"]))
        self.automations.extend(actions)
        self.receipt("automation_complete", "events", {"actions": len(actions)})
        return actions

    def score_risk(self, target):
        base = 10
        if target in self.workloads:
            base += max(0, 10 - int(self.workloads[target]["priority"]))
        if "critical" in str(target):
            base += 40
        score = min(100, base)
        self.risk[target] = {"target": target, "score": score, "recommendation": "allow" if score < 80 else "hold"}
        return self.risk[target]

    def health(self):
        return {
            "workloads": len(self.workloads),
            "scheduled_workloads": len([w for w in self.workloads.values() if w["status"] == "scheduled"]),
            "resources": len(self.resources),
            "deployments": len(self.deployments),
            "healing_plans": len(self.healing_plans),
            "events": len(self.events),
            "automations": len(self.automations),
            "risk_scores": len(self.risk),
            "execution_log": len(self.execution_log),
            "ledger": self.verify_ledger()
        }

    def dashboard(self):
        return {
            "version": "1.9.0",
            "health": self.health(),
            "workloads": list(self.workloads.values()),
            "resources": list(self.resources.values()),
            "deployments": list(self.deployments.values()),
            "healing_plans": list(self.healing_plans.values()),
            "lifecycle": self.lifecycle,
            "events": self.events,
            "automations": self.automations,
            "risk": self.risk,
            "execution_log": self.execution_log
        }

    def export(self, out):
        out = Path(out)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("orchestrator_dashboard.json", json.dumps(self.dashboard(), indent=2, default=str))
            z.writestr("health.json", json.dumps(self.health(), indent=2, default=str))
            z.writestr("workloads.json", json.dumps(list(self.workloads.values()), indent=2))
            z.writestr("resources.json", json.dumps(list(self.resources.values()), indent=2))
            z.writestr("deployments.json", json.dumps(list(self.deployments.values()), indent=2))
            z.writestr("healing_plans.json", json.dumps(list(self.healing_plans.values()), indent=2))
            z.writestr("events.json", json.dumps(self.events, indent=2))
            z.writestr("automations.json", json.dumps(self.automations, indent=2))
            z.writestr("risk.json", json.dumps(self.risk, indent=2))
            z.writestr("lifecycle.json", json.dumps(self.lifecycle, indent=2))
            z.writestr("ledger.json", json.dumps(self.ledger, indent=2))
            for p in sorted(self.plan_dir.glob("*.json")):
                z.write(p, arcname="plans/" + p.name)
        return {"bundle": str(out), "exists": out.exists()}

def seed_demo(td):
    o = AutonomousOrchestrator(Path(td) / "state", Path(td) / "plans")
    r1 = o.add_resource("north", cpu=8, memory=16, storage=100, network=10)
    r2 = o.add_resource("south", cpu=4, memory=8, storage=80, network=5)
    w1 = o.add_workload("operator-dashboard", "service", priority=9, cpu=2, memory=2)
    w2 = o.add_workload("audit-worker", "worker", priority=7, cpu=1, memory=1)
    schedule = o.schedule()
    d = o.deployment_plan(w1["workload"], "rolling")
    deploy = o.execute_deployment(d["deployment"])
    h = o.healing_plan("service:worker", "health_degraded")
    heal = o.execute_healing(h["healing"])
    o.emit_event("service.failed", "service:worker")
    o.emit_event("artifact.ready", w2["workload"])
    auto = o.automate_events()
    bundle = o.export(Path(td) / "orchestrator_bundle.zip")
    return {"resources":[r1,r2], "workloads":[w1,w2], "schedule":schedule, "deploy":deploy, "heal":heal, "automation":auto, "health":o.health(), "bundle":bundle}
