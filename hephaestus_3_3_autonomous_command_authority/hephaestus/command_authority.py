
import json, hashlib, zipfile
from pathlib import Path

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()

class AutonomousCommandAuthority:
    def __init__(self, state_dir="command_state", campaign_dir="campaigns", simulation_dir="simulations"):
        self.state_dir = Path(state_dir); self.state_dir.mkdir(parents=True, exist_ok=True)
        self.campaign_dir = Path(campaign_dir); self.campaign_dir.mkdir(parents=True, exist_ok=True)
        self.simulation_dir = Path(simulation_dir); self.simulation_dir.mkdir(parents=True, exist_ok=True)

        self.command_hierarchy = {}
        self.objectives = {}
        self.resources = {}
        self.missions = {}
        self.campaigns = {}
        self.orchestration = {}
        self.simulations = {}
        self.execution_log = []
        self.audit = []
        self.ledger = []

    def receipt(self, kind, subject, payload):
        prev = self.ledger[-1]["entry_hash"] if self.ledger else "GENESIS"
        ph = digest(payload)
        eh = digest({"kind": kind, "subject": subject, "payload_hash": ph, "prev_hash": prev})
        self.ledger.append({"kind": kind, "subject": subject, "payload_hash": ph, "prev_hash": prev, "entry_hash": eh})

    def verify_ledger(self):
        prev = "GENESIS"
        for i, row in enumerate(self.ledger, 1):
            exp = digest({"kind": row["kind"], "subject": row["subject"], "payload_hash": row["payload_hash"], "prev_hash": prev})
            if row["prev_hash"] != prev or row["entry_hash"] != exp:
                return {"ok": False, "seq": i}
            prev = row["entry_hash"]
        return {"ok": True, "entries": len(self.ledger), "head": prev}

    def define_command_hierarchy(self):
        self.command_hierarchy = {
            "root_authority": {"id": "cmd:root", "role": "strategic_authority", "permissions": ["plan", "approve", "abort"]},
            "regional_commanders": [
                {"id": "cmd:north", "region": "zone-a", "permissions": ["execute", "contain", "recover"]},
                {"id": "cmd:south", "region": "zone-b", "permissions": ["execute", "contain", "recover"]},
                {"id": "cmd:east", "region": "zone-c", "permissions": ["execute", "contain", "recover"]}
            ],
            "field_agents": [
                {"id": "agent:intel", "role": "threat_intelligence"},
                {"id": "agent:response", "role": "response_execution"},
                {"id": "agent:recovery", "role": "recovery_ops"}
            ]
        }
        self.receipt("hierarchy_defined", "command", self.command_hierarchy)
        return self.command_hierarchy

    def add_objective(self, name, priority, success_criteria):
        oid = "objective:" + digest({"name": name, "priority": priority})[:16]
        self.objectives[oid] = {"id": oid, "name": name, "priority": priority, "success_criteria": success_criteria, "status": "active"}
        self.receipt("objective_added", oid, self.objectives[oid])
        return {"objective": oid}

    def allocate_resource(self, name, kind, capacity, region):
        rid = "resource:" + digest({"name": name, "region": region})[:16]
        self.resources[rid] = {"id": rid, "name": name, "kind": kind, "capacity": capacity, "available": capacity, "region": region, "status": "available"}
        self.receipt("resource_allocated", rid, self.resources[rid])
        return {"resource": rid}

    def plan_mission(self, objective, target, threat_level):
        oid = self.objectives[objective]
        mission_type = "containment_campaign" if threat_level >= 80 else "monitoring_campaign"
        mid = "mission:" + digest({"objective": objective, "target": target, "threat": threat_level})[:16]
        steps = ["collect intelligence", "simulate campaign", "allocate resources", "execute response", "verify recovery"]
        if threat_level >= 90:
            steps.insert(3, "federated isolation")
        mission = {
            "id": mid,
            "objective": objective,
            "objective_name": oid["name"],
            "target": target,
            "threat_level": threat_level,
            "mission_type": mission_type,
            "steps": steps,
            "status": "planned"
        }
        self.missions[mid] = mission
        self.receipt("mission_planned", mid, mission)
        return {"mission": mid}

    def simulate_command(self, mission):
        m = self.missions[mission]
        success = 0.96 if m["threat_level"] < 95 else 0.88
        sid = "sim:" + digest({"mission": mission, "steps": m["steps"]})[:16]
        sim = {
            "id": sid,
            "mission": mission,
            "success_probability": success,
            "resource_pressure": "medium" if m["threat_level"] < 90 else "high",
            "approved": success >= 0.85
        }
        self.simulations[sid] = sim
        (self.simulation_dir / (sid.replace(":", "_") + ".json")).write_text(json.dumps(sim, indent=2))
        self.receipt("command_simulated", sid, sim)
        return sim

    def create_campaign(self, mission, grids):
        sim = self.simulate_command(mission)
        cid = "campaign:" + digest({"mission": mission, "grids": grids})[:16]
        campaign = {
            "id": cid,
            "mission": mission,
            "grids": grids,
            "simulation": sim["id"],
            "status": "approved" if sim["approved"] else "held",
            "phases": ["stage", "deploy", "contain", "recover", "report"]
        }
        self.campaigns[cid] = campaign
        (self.campaign_dir / (cid.replace(":", "_") + ".json")).write_text(json.dumps(campaign, indent=2))
        self.receipt("campaign_created", cid, campaign)
        return {"campaign": cid}

    def orchestrate_cross_grid(self, campaign):
        c = self.campaigns[campaign]
        oid = "orchestration:" + digest({"campaign": campaign, "grids": c["grids"]})[:16]
        tasks = []
        for grid in c["grids"]:
            tasks.append({"grid": grid, "action": "execute_campaign_phase", "phase": "contain", "status": "ready"})
            tasks.append({"grid": grid, "action": "sync_defense_memory", "phase": "report", "status": "ready"})
        orchestration = {"id": oid, "campaign": campaign, "tasks": tasks, "status": "ready"}
        self.orchestration[oid] = orchestration
        self.receipt("cross_grid_orchestrated", oid, orchestration)
        return orchestration

    def execute_campaign(self, campaign):
        c = self.campaigns[campaign]
        if c["status"] != "approved":
            result = {"campaign": campaign, "status": "held", "reason": "simulation_not_approved"}
        else:
            orchestration = self.orchestrate_cross_grid(campaign)
            result = {"campaign": campaign, "status": "executed", "orchestration": orchestration["id"], "phases_completed": c["phases"]}
            c["status"] = "executed"
        self.execution_log.append(result)
        self.audit.append({"action": "campaign.executed", "campaign": campaign, "status": result["status"]})
        self.receipt("campaign_executed", campaign, result)
        return result

    def health(self):
        return {
            "hierarchy_defined": bool(self.command_hierarchy),
            "objectives": len(self.objectives),
            "resources": len(self.resources),
            "missions": len(self.missions),
            "campaigns": len(self.campaigns),
            "orchestrations": len(self.orchestration),
            "simulations": len(self.simulations),
            "execution_log": len(self.execution_log),
            "audit_entries": len(self.audit),
            "ledger": self.verify_ledger()
        }

    def dashboard(self):
        return {
            "version": "3.3.0",
            "health": self.health(),
            "command_hierarchy": self.command_hierarchy,
            "objectives": self.objectives,
            "resources": self.resources,
            "missions": self.missions,
            "campaigns": self.campaigns,
            "orchestration": self.orchestration,
            "simulations": self.simulations,
            "execution_log": self.execution_log,
            "audit": self.audit
        }

    def export(self, out):
        out = Path(out)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for name, obj in {
                "command_authority_dashboard.json": self.dashboard(),
                "command_health.json": self.health(),
                "command_hierarchy.json": self.command_hierarchy,
                "strategic_objectives.json": self.objectives,
                "resource_allocations.json": self.resources,
                "missions.json": self.missions,
                "campaigns.json": self.campaigns,
                "cross_grid_orchestration.json": self.orchestration,
                "command_simulations.json": self.simulations,
                "execution_log.json": self.execution_log,
                "audit.json": self.audit,
                "ledger.json": self.ledger
            }.items():
                z.writestr(name, json.dumps(obj, indent=2, default=str))
            for p in sorted(self.campaign_dir.glob("*.json")):
                z.write(p, arcname="campaigns/" + p.name)
            for p in sorted(self.simulation_dir.glob("*.json")):
                z.write(p, arcname="simulations/" + p.name)
        return {"bundle": str(out), "exists": out.exists()}

def seed_demo(td):
    a = AutonomousCommandAuthority(Path(td)/"state", Path(td)/"campaigns", Path(td)/"simulations")
    hierarchy = a.define_command_hierarchy()
    obj = a.add_objective("protect operator dashboard artifact", 10, ["contain threat", "preserve evidence", "recover service"])
    a.allocate_resource("north-response-pool", "response", 8, "zone-a")
    a.allocate_resource("south-recovery-pool", "recovery", 6, "zone-b")
    a.allocate_resource("east-intel-pool", "intelligence", 5, "zone-c")
    mission = a.plan_mission(obj["objective"], "artifact:operator-dashboard", 92)
    campaign = a.create_campaign(mission["mission"], ["north-grid", "south-grid", "east-grid"])
    execution = a.execute_campaign(campaign["campaign"])
    bundle = a.export(Path(td)/"autonomous_command_authority_bundle.zip")
    return {"hierarchy": hierarchy, "objective": obj, "mission": mission, "campaign": campaign, "execution": execution, "health": a.health(), "bundle": bundle}
