
import json, hashlib, zipfile
from pathlib import Path

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()

class Marketplace:
    def __init__(self, package_dir="packages", lock_dir="lockfiles"):
        self.package_dir = Path(package_dir); self.package_dir.mkdir(parents=True, exist_ok=True)
        self.lock_dir = Path(lock_dir); self.lock_dir.mkdir(parents=True, exist_ok=True)
        self.catalog = {}; self.versions = {}; self.installed = {}; self.search_index = {}
        self.trust = {}; self.compatibility = {}; self.audit = []; self.ledger = []

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

    def publish(self, name, version, kind, dependencies=None, compatible_with=None):
        manifest = {
            "name": name, "version": version, "kind": kind,
            "dependencies": dependencies or [],
            "compatible_with": compatible_with or ["2.x"],
            "signature": "SIGNATURE_PLACEHOLDER"
        }
        manifest["package_hash"] = digest(manifest)
        pid = "package:" + digest({"name": name, "version": version})[:16]
        self.catalog[pid] = {"id": pid, "manifest": manifest, "status": "published"}
        self.versions.setdefault(name, []).append({"package": pid, "version": version, "hash": manifest["package_hash"]})
        self.trust[pid] = {"score": 100, "level": "trusted"}
        for term in (name + " " + kind + " " + version).replace("-", " ").replace("_", " ").lower().split():
            self.search_index.setdefault(term, []).append(pid)
        for dep in manifest["dependencies"]:
            self.search_index.setdefault(str(dep).lower(), []).append(pid)
        (self.package_dir / (pid.replace(":", "_") + ".json")).write_text(json.dumps(self.catalog[pid], indent=2))
        self.audit.append({"action": "package.published", "package": pid})
        self.receipt("package_published", pid, self.catalog[pid])
        return {"package": pid}

    def check_compatibility(self, package, target_version="2.0"):
        compat = self.catalog[package]["manifest"]["compatible_with"]
        ok = any(target_version.startswith(x.replace("x", "")) for x in compat)
        result = {"package": package, "target_version": target_version, "compatible": ok}
        self.compatibility[package] = result
        self.receipt("compatibility_checked", package, result)
        return result

    def lockfile(self, package):
        manifest = self.catalog[package]["manifest"]
        deps = []
        for dep in manifest["dependencies"]:
            matches = [pid for pid, rec in self.catalog.items() if rec["manifest"]["name"] == dep]
            if matches:
                pid = matches[-1]
                deps.append({"name": dep, "package": pid, "hash": self.catalog[pid]["manifest"]["package_hash"]})
        lock = {"package": package, "version": manifest["version"], "hash": manifest["package_hash"], "dependencies": deps}
        path = self.lock_dir / (package.replace(":", "_") + ".lock.json")
        path.write_text(json.dumps(lock, indent=2))
        self.receipt("lockfile_created", package, lock)
        return {"path": str(path), "lock": lock}

    def install(self, package, target_version="2.0"):
        if package not in self.catalog:
            return {"status": "missing_package"}
        if not self.check_compatibility(package, target_version)["compatible"]:
            return {"status": "incompatible"}
        lock = self.lockfile(package)
        self.installed[package] = {"package": package, "status": "installed", "lockfile": lock["path"]}
        self.audit.append({"action": "package.installed", "package": package})
        self.receipt("package_installed", package, self.installed[package])
        return {"status": "installed", "package": package, "lockfile": lock["path"]}

    def uninstall(self, package):
        if package in self.installed:
            self.installed[package]["status"] = "uninstalled"
            self.audit.append({"action": "package.uninstalled", "package": package})
            self.receipt("package_uninstalled", package, self.installed[package])
            return {"status": "uninstalled", "package": package}
        return {"status": "not_installed", "package": package}

    def search(self, query):
        hits = []
        for term in query.lower().split():
            hits.extend(self.search_index.get(term, []))
        return {"query": query, "results": sorted(set(hits))}

    def status(self):
        return {
            "packages": len(self.catalog),
            "versioned_names": len(self.versions),
            "installed": len([x for x in self.installed.values() if x["status"] == "installed"]),
            "search_terms": len(self.search_index),
            "trust_scores": len(self.trust),
            "compatibility_checks": len(self.compatibility),
            "audit_entries": len(self.audit),
            "ledger": self.verify_ledger()
        }

    def dashboard(self):
        return {"version": "2.3.0", "status": self.status(), "catalog": self.catalog, "versions": self.versions, "installed": self.installed, "search_index": self.search_index, "trust": self.trust, "compatibility": self.compatibility, "audit": self.audit}

    def export(self, out):
        out = Path(out)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for name, obj in {
                "marketplace_dashboard.json": self.dashboard(),
                "catalog.json": self.catalog,
                "version_registry.json": self.versions,
                "installed.json": self.installed,
                "search_index.json": self.search_index,
                "trust_scores.json": self.trust,
                "compatibility.json": self.compatibility,
                "audit.json": self.audit,
                "ledger.json": self.ledger
            }.items():
                z.writestr(name, json.dumps(obj, indent=2, default=str))
            for p in sorted(self.package_dir.glob("*.json")):
                z.write(p, arcname="packages/" + p.name)
            for p in sorted(self.lock_dir.glob("*.json")):
                z.write(p, arcname="lockfiles/" + p.name)
        return {"bundle": str(out), "exists": out.exists()}

def seed_demo(td):
    m = Marketplace(Path(td) / "packages", Path(td) / "lockfiles")
    db = m.publish("database-schema", "1.0.0", "schema")
    api = m.publish("api-service", "1.0.0", "service", dependencies=["database-schema"])
    dash = m.publish("operator-dashboard", "1.0.0", "dashboard", dependencies=["api-service"])
    install = m.install(dash["package"], "2.3")
    search = m.search("operator dashboard")
    uninstall = m.uninstall(dash["package"])
    bundle = m.export(Path(td) / "artifact_marketplace_bundle.zip")
    return {"packages": [db, api, dash], "install": install, "search": search, "uninstall": uninstall, "status": m.status(), "bundle": bundle}
