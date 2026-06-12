
import json, hashlib, zipfile
from pathlib import Path

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()

class TrustAuthority:
    def __init__(self, receipts="receipts"):
        self.receipts = Path(receipts); self.receipts.mkdir(parents=True, exist_ok=True)
        self.publishers = {}; self.artifacts = {}; self.signatures = {}
        self.trust_chain = []; self.revocations = {}; self.install_gates = {}
        self.execution_gates = {}; self.tamper_events = []; self.provenance = []
        self.ledger = []

    def receipt(self, kind, subject, payload):
        prev = self.ledger[-1]["entry_hash"] if self.ledger else "GENESIS"
        ph = digest(payload)
        eh = digest({"kind":kind, "subject":subject, "payload_hash":ph, "prev_hash":prev})
        row = {"kind":kind, "subject":subject, "payload_hash":ph, "prev_hash":prev, "entry_hash":eh}
        self.ledger.append(row)
        (self.receipts/(eh[:16]+".json")).write_text(json.dumps(row, indent=2))
        return row

    def verify_ledger(self):
        prev = "GENESIS"
        for i, row in enumerate(self.ledger, start=1):
            exp = digest({"kind":row["kind"], "subject":row["subject"], "payload_hash":row["payload_hash"], "prev_hash":prev})
            if row["prev_hash"] != prev or row["entry_hash"] != exp:
                return {"ok":False, "seq":i}
            prev = row["entry_hash"]
        return {"ok":True, "entries":len(self.ledger), "head":prev}

    def publisher(self, name, level="standard"):
        pid = "publisher:" + digest({"name":name, "level":level})[:16]
        self.publishers[pid] = {"id":pid, "name":name, "level":level, "status":"trusted", "public_key":"PUBLIC_KEY_PLACEHOLDER"}
        self.trust_chain.append({"publisher":pid, "issuer":"hephaestus-root", "status":"trusted"})
        self.receipt("publisher_registered", pid, self.publishers[pid])
        return {"publisher":pid}

    def artifact(self, name, version, content, publisher):
        aid = "artifact:" + digest({"name":name, "version":version, "publisher":publisher})[:16]
        self.artifacts[aid] = {"id":aid, "name":name, "version":version, "publisher":publisher, "content_hash":hashlib.sha256(content.encode()).hexdigest(), "status":"registered"}
        self.receipt("artifact_registered", aid, self.artifacts[aid])
        return {"artifact":aid}

    def sign(self, artifact, publisher):
        if publisher not in self.publishers or self.publishers[publisher]["status"] != "trusted":
            return {"status":"publisher_untrusted"}
        payload = {"artifact":artifact, "publisher":publisher, "content_hash":self.artifacts[artifact]["content_hash"]}
        sig = "sig:" + digest(payload)[:32]
        self.signatures[artifact] = {"signature":sig, "artifact":artifact, "publisher":publisher, "payload_hash":digest(payload), "algorithm":"SHA256_PLACEHOLDER_SIGNATURE", "status":"signed"}
        self.artifacts[artifact]["status"] = "signed"
        self.receipt("artifact_signed", artifact, self.signatures[artifact])
        return {"signature":sig, "artifact":artifact}

    def verify(self, artifact):
        if artifact in self.revocations:
            return {"artifact":artifact, "verified":False, "reason":"revoked"}
        sig = self.signatures.get(artifact)
        if not sig:
            return {"artifact":artifact, "verified":False, "reason":"missing_signature"}
        publisher = sig["publisher"]
        payload = {"artifact":artifact, "publisher":publisher, "content_hash":self.artifacts[artifact]["content_hash"]}
        ok = publisher in self.publishers and self.publishers[publisher]["status"] == "trusted" and sig["payload_hash"] == digest(payload)
        result = {"artifact":artifact, "verified":ok, "reason":"ok" if ok else "signature_mismatch"}
        self.receipt("signature_verified", artifact, result)
        return result

    def revoke(self, artifact, reason):
        self.revocations[artifact] = {"artifact":artifact, "reason":reason, "status":"revoked"}
        if artifact in self.artifacts:
            self.artifacts[artifact]["status"] = "revoked"
        self.receipt("artifact_revoked", artifact, self.revocations[artifact])
        return self.revocations[artifact]

    def install_gate(self, artifact):
        v = self.verify(artifact)
        gate = {"artifact":artifact, "gate":"install", "decision":"allow" if v["verified"] else "deny", "verification":v}
        self.install_gates[artifact] = gate
        self.receipt("install_gate", artifact, gate)
        return gate

    def execution_gate(self, artifact):
        v = self.verify(artifact)
        gate = {"artifact":artifact, "gate":"execution", "decision":"allow" if v["verified"] else "deny", "verification":v}
        self.execution_gates[artifact] = gate
        self.receipt("execution_gate", artifact, gate)
        return gate

    def tamper_check(self, artifact, observed_content):
        observed = hashlib.sha256(observed_content.encode()).hexdigest()
        expected = self.artifacts[artifact]["content_hash"]
        result = {"artifact":artifact, "tampered":observed != expected, "expected_hash":expected, "observed_hash":observed}
        if result["tampered"]:
            self.tamper_events.append(result)
        self.receipt("tamper_check", artifact, result)
        return result

    def provenance_receipt(self, artifact):
        record = {"artifact":artifact, "publisher":self.artifacts[artifact]["publisher"], "content_hash":self.artifacts[artifact]["content_hash"], "signature":self.signatures.get(artifact), "status":self.artifacts[artifact]["status"]}
        prid = "provenance:" + digest(record)[:16]
        record["id"] = prid
        self.provenance.append(record)
        (self.receipts/(prid.replace(":","_")+".json")).write_text(json.dumps(record, indent=2, default=str))
        self.receipt("provenance_receipt", prid, record)
        return {"provenance":prid}

    def status(self):
        return {"publishers":len(self.publishers), "artifacts":len(self.artifacts), "signatures":len(self.signatures), "trust_chain":len(self.trust_chain), "revocations":len(self.revocations), "install_gates":len(self.install_gates), "execution_gates":len(self.execution_gates), "tamper_events":len(self.tamper_events), "provenance_receipts":len(self.provenance), "ledger":self.verify_ledger()}

    def dashboard(self):
        return {"version":"2.4.0", "status":self.status(), "publishers":self.publishers, "artifacts":self.artifacts, "signatures":self.signatures, "trust_chain":self.trust_chain, "revocations":self.revocations, "install_gates":self.install_gates, "execution_gates":self.execution_gates, "tamper_events":self.tamper_events, "provenance":self.provenance}

    def export(self, out):
        out = Path(out)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for name, obj in {
                "trust_dashboard.json":self.dashboard(),
                "publishers.json":self.publishers,
                "artifacts.json":self.artifacts,
                "signatures.json":self.signatures,
                "trust_chain.json":self.trust_chain,
                "revocations.json":self.revocations,
                "install_gates.json":self.install_gates,
                "execution_gates.json":self.execution_gates,
                "tamper_events.json":self.tamper_events,
                "provenance.json":self.provenance,
                "ledger.json":self.ledger
            }.items():
                z.writestr(name, json.dumps(obj, indent=2, default=str))
            for p in sorted(self.receipts.glob("*.json")):
                z.write(p, arcname="receipts/"+p.name)
        return {"bundle":str(out), "exists":out.exists()}

def seed_demo(td):
    t = TrustAuthority(Path(td)/"receipts")
    pub = t.publisher("hephaestus-root-publisher", "root")
    art = t.artifact("operator-dashboard", "1.0.0", "dashboard api database workflow", pub["publisher"])
    sig = t.sign(art["artifact"], pub["publisher"])
    verify = t.verify(art["artifact"])
    install = t.install_gate(art["artifact"])
    execute = t.execution_gate(art["artifact"])
    clean = t.tamper_check(art["artifact"], "dashboard api database workflow")
    tampered = t.tamper_check(art["artifact"], "dashboard api hacked workflow")
    prov = t.provenance_receipt(art["artifact"])
    bundle = t.export(Path(td)/"trust_signature_bundle.zip")
    return {"publisher":pub, "artifact":art, "signature":sig, "verify":verify, "install":install, "execute":execute, "clean":clean, "tampered":tampered, "provenance":prov, "status":t.status(), "bundle":bundle}
