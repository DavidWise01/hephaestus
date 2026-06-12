
import json, time, hashlib, zipfile
from pathlib import Path

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()

class Cluster:
    def __init__(self, state="cluster_state"):
        self.state = Path(state)
        self.state.mkdir(parents=True, exist_ok=True)
        self.nodes = {}
        self.membership = {}
        self.routes = {}
        self.replications = []
        self.elections = []
        self.snapshots = []
        self.failures = []
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

    def node(self, name, endpoint, role="follower"):
        nid = "node:" + digest({"name": name, "endpoint": endpoint})[:16]
        self.nodes[nid] = {"id": nid, "name": name, "role": role, "status": "registered", "health": "unknown", "endpoint": endpoint}
        self.receipt("node_registered", nid, self.nodes[nid])
        return {"node": nid, "name": name}

    def join(self, node, cluster="hephaestus-cluster"):
        mid = "member:" + digest({"node": node, "cluster": cluster})[:16]
        self.membership[mid] = {"id": mid, "node": node, "cluster": cluster, "status": "active"}
        self.receipt("node_joined", mid, self.membership[mid])
        return {"membership": mid}

    def heartbeat(self, node, health="ok"):
        self.nodes[node]["status"] = "online" if health == "ok" else "degraded"
        self.nodes[node]["health"] = health
        self.receipt("heartbeat", node, {"health": health})

    def elect(self):
        online = sorted([n for n in self.nodes.values() if n["status"] == "online"], key=lambda x: x["id"])
        leader = online[0]["id"] if online else ""
        for n in self.nodes.values():
            n["role"] = "leader" if n["id"] == leader else "follower"
        election = {"id": "election:" + digest({"leader": leader, "term": len(self.elections)+1})[:16], "term": len(self.elections)+1, "leader": leader, "status": "complete" if leader else "failed"}
        self.elections.append(election)
        self.receipt("leader_elected", election["id"], election)
        return election

    def route(self, path, home_node):
        rid = "route:" + digest({"path": path, "node": home_node})[:16]
        self.routes[rid] = {"id": rid, "path": path, "home_node": home_node, "status": "active"}
        self.receipt("route_added", rid, self.routes[rid])
        return {"route": rid}

    def cross_route(self, path):
        match = next((r for r in self.routes.values() if r["path"] == path and r["status"] == "active"), None)
        if not match:
            return {"path": path, "status": "not_found", "node": None}
        node = self.nodes.get(match["home_node"])
        if node and node["status"] == "online":
            return {"path": path, "status": "routed", "node": node["id"], "endpoint": node["endpoint"]}
        leader = next((n for n in self.nodes.values() if n["role"] == "leader" and n["status"] == "online"), None)
        return {"path": path, "status": "failover" if leader else "unavailable", "node": leader["id"] if leader else None}

    def replicate(self, src, dst, kind, payload):
        item = {"id": "repl:" + digest({"src": src, "dst": dst, "kind": kind, "payload": payload})[:16], "src": src, "dst": dst, "kind": kind, "payload_hash": digest(payload), "status": "complete"}
        self.replications.append(item)
        self.receipt("replication", item["id"], item)
        return {"replication": item["id"], "status": "complete"}

    def replicate_all(self, src, kind, payload):
        return [self.replicate(src, n["id"], kind, payload) for n in self.nodes.values() if n["id"] != src and n["status"] == "online"]

    def snapshot(self, cluster="hephaestus-cluster"):
        data = self.dashboard()
        h = digest(data)
        sid = "snapshot:" + h[:16]
        path = self.state / (sid.replace(":","_") + ".json")
        path.write_text(json.dumps(data, indent=2))
        snap = {"id": sid, "cluster": cluster, "path": str(path), "hash": h}
        self.snapshots.append(snap)
        self.receipt("snapshot", sid, {"hash": h})
        return {"snapshot": sid, "path": str(path)}

    def health(self):
        return {
            "nodes": len(self.nodes),
            "online": len([n for n in self.nodes.values() if n["status"] == "online"]),
            "leaders": len([n for n in self.nodes.values() if n["role"] == "leader"]),
            "routes": len(self.routes),
            "replications": len(self.replications),
            "snapshots": len(self.snapshots),
            "failures": len(self.failures),
            "ledger": self.verify_ledger()
        }

    def dashboard(self):
        return {
            "version": "1.3.0",
            "health": self.health(),
            "nodes": list(self.nodes.values()),
            "membership": list(self.membership.values()),
            "routes": list(self.routes.values()),
            "replications": self.replications,
            "elections": self.elections,
            "failures": self.failures
        }

    def export(self, out):
        out = Path(out)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("cluster_dashboard.json", json.dumps(self.dashboard(), indent=2))
            z.writestr("nodes.json", json.dumps(list(self.nodes.values()), indent=2))
            z.writestr("membership.json", json.dumps(list(self.membership.values()), indent=2))
            z.writestr("routes.json", json.dumps(list(self.routes.values()), indent=2))
            z.writestr("replications.json", json.dumps(self.replications, indent=2))
            z.writestr("elections.json", json.dumps(self.elections, indent=2))
            z.writestr("ledger.json", json.dumps(self.ledger, indent=2))
            for p in sorted(self.state.glob("*.json")):
                z.write(p, arcname="cluster_state/" + p.name)
        return {"bundle": str(out), "exists": out.exists()}

def seed_demo(td):
    c = Cluster(Path(td) / "state")
    n1 = c.node("north", "http://127.0.0.1:8201")
    n2 = c.node("south", "http://127.0.0.1:8202")
    n3 = c.node("east", "http://127.0.0.1:8203")
    for n in [n1,n2,n3]:
        c.join(n["node"])
        c.heartbeat(n["node"])
    election = c.elect()
    c.route("/api/status", n1["node"])
    c.route("/dashboard", n2["node"])
    c.route("/reports", n3["node"])
    repl = c.replicate_all(election["leader"], "state", {"runtime":"active","version":"1.3.0"})
    routes = [c.cross_route("/dashboard"), c.cross_route("/missing")]
    snap = c.snapshot()
    bundle = c.export(Path(td) / "cluster_bundle.zip")
    return {"nodes":[n1,n2,n3],"election":election,"replications":repl,"routes":routes,"snapshot":snap,"health":c.health(),"bundle":bundle}
