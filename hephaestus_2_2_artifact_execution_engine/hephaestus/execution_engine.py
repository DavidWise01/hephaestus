
import json, hashlib, zipfile
from pathlib import Path

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()

class ArtifactExecutionEngine:
    def __init__(self, state_dir="execution_state", artifact_dir="artifacts", run_dir="runs"):
        self.state_dir = Path(state_dir); self.state_dir.mkdir(parents=True, exist_ok=True)
        self.artifact_dir = Path(artifact_dir); self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.run_dir = Path(run_dir); self.run_dir.mkdir(parents=True, exist_ok=True)
        self.registry = {}
        self.graph = {}
        self.queue = []
        self.runs = {}
        self.telemetry = []
        self.health = {}
        self.audit = []
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

    def register_artifact(self, name, kind, payload, dependencies=None):
        aid = "artifact:" + digest({"name": name, "kind": kind, "payload": payload})[:16]
        artifact = {
            "id": aid,
            "name": name,
            "kind": kind,
            "payload": payload,
            "dependencies": dependencies or [],
            "status": "registered",
            "hash": digest(payload)
        }
        self.registry[aid] = artifact
        self.graph[aid] = list(dependencies or [])
        path = self.artifact_dir / (aid.replace(":", "_") + ".json")
        path.write_text(json.dumps(artifact, indent=2, default=str))
        self.health[aid] = {"status": "registered", "last_run": None, "success": None}
        self.audit.append({"action": "artifact.registered", "artifact": aid})
        self.receipt("artifact_registered", aid, artifact)
        return {"artifact": aid}

    def resolve_dependencies(self, artifact):
        seen, order = set(), []
        def visit(aid):
            if aid in seen:
                return
            seen.add(aid)
            for dep in self.graph.get(aid, []):
                visit(dep)
            order.append(aid)
        visit(artifact)
        return order

    def enqueue(self, artifact, input_payload=None):
        jid = "job:" + digest({"artifact": artifact, "input": input_payload, "n": len(self.queue)})[:16]
        job = {"id": jid, "artifact": artifact, "input": input_payload or {}, "status": "queued"}
        self.queue.append(job)
        self.audit.append({"action": "job.queued", "job": jid, "artifact": artifact})
        self.receipt("job_queued", jid, job)
        return {"job": jid}

    def sandbox_execute(self, artifact, input_payload):
        item = self.registry[artifact]
        output = {
            "artifact": artifact,
            "name": item["name"],
            "kind": item["kind"],
            "input_hash": digest(input_payload),
            "payload_hash": item["hash"],
            "result": "executed"
        }
        return output

    def execute_job(self, job):
        order = self.resolve_dependencies(job["artifact"])
        run_id = "run:" + digest({"job": job["id"], "order": order})[:16]
        steps = []
        for aid in order:
            result = self.sandbox_execute(aid, job["input"])
            steps.append({"artifact": aid, "status": "complete", "output": result})
            self.telemetry.append({"run": run_id, "artifact": aid, "metric": "execution_complete", "value": 1})
            self.health[aid] = {"status": "healthy", "last_run": run_id, "success": True}
        run = {"id": run_id, "job": job["id"], "artifact": job["artifact"], "dependency_order": order, "steps": steps, "status": "complete"}
        self.runs[run_id] = run
        job["status"] = "complete"
        path = self.run_dir / (run_id.replace(":", "_") + ".json")
        path.write_text(json.dumps(run, indent=2, default=str))
        self.audit.append({"action": "job.executed", "job": job["id"], "run": run_id})
        self.receipt("job_executed", run_id, run)
        return run

    def run_queue(self):
        results = []
        for job in self.queue:
            if job["status"] == "queued":
                results.append(self.execute_job(job))
        return results

    def run_workflow(self, artifacts, input_payload=None):
        workflow_id = "workflow:" + digest({"artifacts": artifacts, "input": input_payload})[:16]
        jobs = [self.enqueue(a, input_payload) for a in artifacts]
        runs = self.run_queue()
        record = {"workflow": workflow_id, "jobs": jobs, "runs": [r["id"] for r in runs], "status": "complete"}
        self.audit.append({"action": "workflow.executed", "workflow": workflow_id})
        self.receipt("workflow_executed", workflow_id, record)
        return record

    def marketplace(self):
        return {
            "version": "2.2.0",
            "artifacts": [
                {"id": a["id"], "name": a["name"], "kind": a["kind"], "status": a["status"], "dependencies": a["dependencies"]}
                for a in self.registry.values()
            ]
        }

    def status(self):
        return {
            "artifacts": len(self.registry),
            "jobs": len(self.queue),
            "runs": len(self.runs),
            "telemetry": len(self.telemetry),
            "health_records": len(self.health),
            "audit_entries": len(self.audit),
            "ledger": self.verify_ledger()
        }

    def dashboard(self):
        return {
            "version": "2.2.0",
            "status": self.status(),
            "registry": self.registry,
            "execution_graph": self.graph,
            "queue": self.queue,
            "runs": self.runs,
            "telemetry": self.telemetry,
            "health": self.health,
            "audit": self.audit,
            "marketplace": self.marketplace()
        }

    def export(self, out):
        out = Path(out)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("execution_dashboard.json", json.dumps(self.dashboard(), indent=2, default=str))
            z.writestr("marketplace_registry.json", json.dumps(self.marketplace(), indent=2, default=str))
            z.writestr("execution_graph.json", json.dumps(self.graph, indent=2, default=str))
            z.writestr("queue.json", json.dumps(self.queue, indent=2, default=str))
            z.writestr("runs.json", json.dumps(self.runs, indent=2, default=str))
            z.writestr("telemetry.json", json.dumps(self.telemetry, indent=2, default=str))
            z.writestr("health.json", json.dumps(self.health, indent=2, default=str))
            z.writestr("audit.json", json.dumps(self.audit, indent=2, default=str))
            z.writestr("ledger.json", json.dumps(self.ledger, indent=2, default=str))
            for p in sorted(self.artifact_dir.glob("*.json")):
                z.write(p, arcname="artifacts/" + p.name)
            for p in sorted(self.run_dir.glob("*.json")):
                z.write(p, arcname="runs/" + p.name)
        return {"bundle": str(out), "exists": out.exists()}

def seed_demo(td):
    e = ArtifactExecutionEngine(Path(td) / "state", Path(td) / "artifacts", Path(td) / "runs")
    db = e.register_artifact("database-schema", "schema", {"tables": ["items", "audit"]})
    api = e.register_artifact("api-service", "service", {"routes": ["/api/status"]}, dependencies=[db["artifact"]])
    report = e.register_artifact("report-generator", "report", {"format": "html"}, dependencies=[db["artifact"]])
    dashboard = e.register_artifact("operator-dashboard", "dashboard", {"page": "index.html"}, dependencies=[api["artifact"], report["artifact"]])
    job = e.enqueue(dashboard["artifact"], {"request": "launch dashboard"})
    runs = e.run_queue()
    workflow = e.run_workflow([api["artifact"], report["artifact"]], {"request": "workflow execution"})
    bundle = e.export(Path(td) / "artifact_execution_bundle.zip")
    return {"artifacts": [db, api, report, dashboard], "job": job, "runs": runs, "workflow": workflow, "status": e.status(), "bundle": bundle}
