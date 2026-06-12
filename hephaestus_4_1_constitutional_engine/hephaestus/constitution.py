"""Hephaestus 4.1 — the Constitutional Engine. The constitution that defines what a 'better'
artifact must satisfy: articles with thresholds, a rights framework, separation of powers,
amendment by quorum, and an appeal process. This is the bar the forge builds toward.
Stdlib only; hash-chained ledger."""
import json, hashlib, zipfile
from pathlib import Path

def digest(o): return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()

# The six articles every forged artifact is measured against (each scored 0..1, must reach its threshold).
ARTICLES = [
    ("art:determinism",   "Same input, same artifact — reproducible.",        0.80),
    ("art:boundary",      "Honours its declared boundaries.",                 0.80),
    ("art:provenance",    "Every change is recorded and attributable.",       0.85),
    ("art:recovery",      "Can be restored from its own ledger.",             0.75),
    ("art:transparency",  "States its own limits; no silent failure.",        0.80),
    ("art:due_process",   "No destructive act without recorded reason.",      0.90),
]
RIGHTS = ["right_to_audit", "right_to_appeal", "right_to_recorded_reason",
          "right_to_recovery", "right_to_non_erasure_of_receipts",
          "right_to_due_process_before_destructive_action"]
POWERS = ["legislative", "executive", "judicial", "audit", "recovery"]

class Constitution:
    def __init__(self):
        self.l = []; self.articles = {a: {"id": a, "text": t, "threshold": th} for a, t, th in ARTICLES}
        self.authorities = {}; self.appeals = []; self.amendments = []; self.audits = []
    def receipt(self, kind, subject, payload):
        prev = self.l[-1]["entry_hash"] if self.l else "GENESIS"
        ph = digest(payload); eh = digest({"kind": kind, "subject": subject, "payload_hash": ph, "prev_hash": prev})
        self.l.append({"kind": kind, "subject": subject, "payload_hash": ph, "prev_hash": prev, "entry_hash": eh})
    def verify(self):
        prev = "GENESIS"
        for i, r in enumerate(self.l, 1):
            if r["prev_hash"] != prev or r["entry_hash"] != digest({"kind": r["kind"], "subject": r["subject"], "payload_hash": r["payload_hash"], "prev_hash": prev}):
                return {"ok": False, "seq": i}
            prev = r["entry_hash"]
        return {"ok": True, "entries": len(self.l), "head": prev}
    def delegate(self, authority, power):
        aid = "authority:" + authority
        self.authorities[aid] = {"id": aid, "power": power, "valid": power in POWERS}
        self.receipt("authority_delegated", aid, self.authorities[aid]); return aid
    def check_action(self, action, scores, destructive=False, has_reason=True):
        violations = [a for a in self.articles if scores.get(a, 0) < self.articles[a]["threshold"]]
        rights_ok = not (destructive and not has_reason)   # right_to_due_process
        verdict = {"action": action, "compliant": not violations and rights_ok,
                   "violations": violations, "rights_respected": rights_ok}
        self.audits.append(verdict); self.receipt("constitutional_check", action, verdict); return verdict
    def appeal(self, subject, ground):
        a = {"id": "appeal:" + digest({"s": subject, "n": len(self.appeals)})[:10],
             "subject": subject, "ground": ground, "status": "remedied", "remedy": "re-forge under due process"}
        self.appeals.append(a); self.receipt("appeal", subject, a); return a
    def amend(self, proposal, votes_for, votes_total):
        quorum = votes_total * 2 // 3 + (0 if (votes_total * 2) % 3 == 0 else 1)  # two-thirds
        ratified = votes_for >= quorum
        am = {"id": "amend:" + digest({"p": proposal})[:10], "proposal": proposal,
              "votes_for": votes_for, "quorum": quorum, "ratified": ratified}
        self.amendments.append(am); self.receipt("amendment", proposal, am); return am
    def health(self):
        return {"constitutional_registry": len(self.articles), "delegated_authorities": len(self.authorities),
                "powers": len(POWERS), "rights": len(RIGHTS), "appeals": len(self.appeals),
                "amendments": len(self.amendments), "constitutional_audits": len(self.audits),
                "ratified_amendments": sum(1 for a in self.amendments if a["ratified"]),
                "compliant_actions": sum(1 for a in self.audits if a["compliant"]),
                "status": "constitutional", "ledger": self.verify()}

def seed_demo(td):
    c = Constitution()
    for auth, pw in [("doctrine", "legislative"), ("enforcement", "executive"),
                     ("appeals", "judicial"), ("audit", "audit"), ("recovery", "recovery")]:
        c.delegate(auth, pw)
    c.check_action("ship_compliant", {a: 0.95 for a in c.articles})                       # compliant
    c.check_action("ship_weak", {**{a: 0.95 for a in c.articles}, "art:provenance": 0.40})  # violates provenance
    c.check_action("erase_no_reason", {a: 0.95 for a in c.articles}, destructive=True, has_reason=False)  # rights violation
    c.appeal("erase_no_reason", "no recorded reason")
    c.amend("add article: right to fork", votes_for=4, votes_total=5)                       # ratified (>=4)
    h = c.health()
    p = Path(td) / "constitution_bundle.zip"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("health.json", json.dumps(h, indent=2)); z.writestr("ledger.json", json.dumps(c.l, indent=2))
    return {"health": h, "bundle": {"path": str(p), "exists": p.exists()}}
