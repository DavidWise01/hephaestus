
import json, hashlib, zipfile
from pathlib import Path

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()

class DistributedState:
    def __init__(self, snapshots="state_snapshots"):
        self.snapshots = Path(snapshots)
        self.snapshots.mkdir(parents=True, exist_ok=True)
        self.nodes = {}
        self.store = {}
        self.versions = {}
        self.journal = []
        self.replications = []
        self.conflicts = []
        self.locks = {}
        self.cache = {}
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

    def add_node(self, name):
        nid = "node:" + digest(name)[:16]
        self.nodes[nid] = {"id": nid, "name": name, "status": "online"}
        self.receipt("node_added", nid, self.nodes[nid])
        return {"node": nid, "name": name}

    def lock(self, key, owner):
        if key in self.locks and self.locks[key]["status"] == "held":
            return {"ok": False, "held_by": self.locks[key]["owner"]}
        self.locks[key] = {"key": key, "owner": owner, "status": "held"}
        self.receipt("lock_acquired", key, self.locks[key])
        return {"ok": True, "key": key, "owner": owner}

    def unlock(self, key, owner):
        if key in self.locks and self.locks[key]["owner"] == owner:
            self.locks[key]["status"] = "released"
            self.receipt("lock_released", key, self.locks[key])
            return {"ok": True}
        return {"ok": False}

    def put(self, key, value, node, expected_version=None):
        current = self.versions.get(key, 0)
        if expected_version is not None and expected_version != current:
            self.conflicts.append({
                "key": key,
                "expected": expected_version,
                "actual": current,
                "resolution": "last_writer_wins",
                "incoming": value,
                "existing": self.store.get(key)
            })
        new_version = current + 1
        obj = {"key": key, "value": value, "version": new_version, "node": node, "hash": digest(value)}
        self.store[key] = obj
        self.cache[key] = obj
        self.versions[key] = new_version
        event = {"op": "put", "key": key, "version": new_version, "node": node, "hash": obj["hash"]}
        self.journal.append(event)
        self.receipt("state_put", key, event)
        return obj

    def get(self, key):
        return self.cache.get(key) or self.store.get(key)

    def replicate(self, key, src, dst):
        obj = self.store.get(key)
        if not obj:
            return {"ok": False, "reason": "missing"}
        event = {"key": key, "src": src, "dst": dst, "version": obj["version"], "hash": obj["hash"], "status": "replicated"}
        self.replications.append(event)
        self.receipt("state_replicated", key, event)
        return event

    def replicate_all(self, key, src):
        return [self.replicate(key, src, nid) for nid in self.nodes if nid != src and self.nodes[nid]["status"] == "online"]

    def consensus(self, key):
        obj = self.store.get(key)
        return {"key": key, "committed": bool(obj), "version": obj["version"] if obj else 0, "hash": obj["hash"] if obj else None}

    def health(self):
        return {
            "nodes": len(self.nodes),
            "online": len([n for n in self.nodes.values() if n["status"] == "online"]),
            "keys": len(self.store),
            "journal_entries": len(self.journal),
            "replications": len(self.replications),
            "conflicts": len(self.conflicts),
            "locks": len(self.locks),
            "cache_entries": len(self.cache),
            "ledger": self.verify_ledger()
        }

    def dashboard(self):
        return {
            "version": "1.4.0",
            "health": self.health(),
            "nodes": list(self.nodes.values()),
            "store": self.store,
            "journal": self.journal,
            "replications": self.replications,
            "conflicts": self.conflicts,
            "locks": self.locks,
            "cache": self.cache
        }

    def snapshot(self):
        data = self.dashboard()
        h = digest(data)
        sid = "snapshot:" + h[:16]
        path = self.snapshots / (sid.replace(":", "_") + ".json")
        path.write_text(json.dumps(data, indent=2, default=str))
        self.receipt("snapshot", sid, {"hash": h, "path": str(path)})
        return {"snapshot": sid, "path": str(path), "hash": h}

    def export(self, out):
        out = Path(out)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("distributed_state_dashboard.json", json.dumps(self.dashboard(), indent=2, default=str))
            z.writestr("nodes.json", json.dumps(list(self.nodes.values()), indent=2))
            z.writestr("store.json", json.dumps(self.store, indent=2, default=str))
            z.writestr("journal.json", json.dumps(self.journal, indent=2, default=str))
            z.writestr("replications.json", json.dumps(self.replications, indent=2, default=str))
            z.writestr("conflicts.json", json.dumps(self.conflicts, indent=2, default=str))
            z.writestr("locks.json", json.dumps(self.locks, indent=2, default=str))
            z.writestr("ledger.json", json.dumps(self.ledger, indent=2, default=str))
            for p in sorted(self.snapshots.glob("*.json")):
                z.write(p, arcname="state_snapshots/" + p.name)
        return {"bundle": str(out), "exists": out.exists()}

def seed_demo(td):
    ds = DistributedState(Path(td) / "snapshots")
    n1 = ds.add_node("north")
    n2 = ds.add_node("south")
    n3 = ds.add_node("east")
    ds.lock("config:runtime", n1["node"])
    obj1 = ds.put("config:runtime", {"mode": "active", "version": "1.4.0"}, n1["node"])
    ds.unlock("config:runtime", n1["node"])
    repl1 = ds.replicate_all("config:runtime", n1["node"])
    obj2 = ds.put("artifact:demo", {"status": "released", "owner": "hephaestus"}, n2["node"])
    repl2 = ds.replicate_all("artifact:demo", n2["node"])
    ds.put("config:runtime", {"mode": "active", "version": "1.4.1-conflict-test"}, n3["node"], expected_version=0)
    consensus = ds.consensus("config:runtime")
    snap = ds.snapshot()
    bundle = ds.export(Path(td) / "distributed_state_bundle.zip")
    return {"nodes":[n1,n2,n3],"objects":[obj1,obj2],"replications":repl1+repl2,"consensus":consensus,"snapshot":snap,"health":ds.health(),"bundle":bundle}
