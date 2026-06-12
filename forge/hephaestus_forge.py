"""HEPHAESTUS · THE FORGE — an artifact that builds better artifacts.

The forge takes an artifact (scored against the six constitutional articles) and, pass by pass,
applies a named craft to its WEAKEST article, emitting a NEW artifact that is strictly better than
its parent — a hash-linked lineage that climbs until every article meets its threshold and the
artifact is *constitutional*. The forge is itself an artifact (this file); given an artifact, it
returns a better one. That is the whole idea, made to run. Stdlib only.

    python hephaestus_forge.py            # forge a weak demo artifact to compliance, print the lineage
    python hephaestus_forge.py --json
"""
import json, hashlib, sys

# the constitution's six articles and the score each must reach (mirrors hephaestus 4.1)
THRESHOLDS = {
    "determinism": 0.80, "boundary": 0.80, "provenance": 0.85,
    "recovery": 0.75, "transparency": 0.80, "due_process": 0.90,
}
# the craft applied to each article when the forge works it (a named technique)
CRAFT = {
    "determinism": "pin the seed",        "boundary":    "fence the scope",
    "provenance":  "chain the receipt",   "recovery":    "ledger the restore-point",
    "transparency":"surface the limit",   "due_process": "gate the destructive act",
}
def digest(o): return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()

def artifact(name, scores, gen=0, parent=None, craft=None):
    a = {"name": name, "gen": gen, "parent": parent, "last_craft": craft,
         "scores": dict(scores)}
    a["total"] = round(sum(a["scores"].values()), 6)
    a["compliant"] = all(a["scores"][k] >= THRESHOLDS[k] for k in THRESHOLDS)
    a["id"] = "artifact:" + digest({"name": name, "gen": gen, "scores": a["scores"]})[:16]
    return a

def deficits(a):
    return {k: THRESHOLDS[k] - a["scores"].get(k, 0) for k in THRESHOLDS if a["scores"].get(k, 0) < THRESHOLDS[k]}

def forge_pass(a, craft_strength=0.6):
    """Apply one craft to the weakest deficient article -> a NEW, strictly-better child artifact."""
    d = deficits(a)
    if not d:
        return None  # already constitutional; nothing to improve
    worst = max(d, key=d.get)
    ceiling = min(1.0, THRESHOLDS[worst] + 0.05)          # craft overshoots the bar a little
    s = dict(a["scores"])
    s[worst] = round(s[worst] + (ceiling - s[worst]) * craft_strength, 6)  # diminishing-returns lift
    return artifact(a["name"], s, gen=a["gen"] + 1, parent=a["id"], craft=(worst, CRAFT[worst]))

class Forge:
    def __init__(self): self.ledger = []
    def receipt(self, kind, subject, payload):
        prev = self.ledger[-1]["entry_hash"] if self.ledger else "GENESIS"
        ph = digest(payload); eh = digest({"kind": kind, "subject": subject, "payload_hash": ph, "prev_hash": prev})
        self.ledger.append({"kind": kind, "subject": subject, "payload_hash": ph, "prev_hash": prev, "entry_hash": eh})
    def verify(self):
        prev = "GENESIS"
        for i, r in enumerate(self.ledger, 1):
            if r["prev_hash"] != prev or r["entry_hash"] != digest({"kind": r["kind"], "subject": r["subject"], "payload_hash": r["payload_hash"], "prev_hash": prev}):
                return {"ok": False, "seq": i}
            prev = r["entry_hash"]
        return {"ok": True, "entries": len(self.ledger), "head": prev}
    def build_better(self, seed, max_passes=20):
        """Forge the seed artifact upward until constitutional (or budget spent). Returns the lineage."""
        a = seed; lineage = [a]; self.receipt("artifact_received", a["id"], {"total": a["total"], "compliant": a["compliant"]})
        for _ in range(max_passes):
            if a["compliant"]: break
            nxt = forge_pass(a)
            if nxt is None or nxt["total"] <= a["total"]:  # safety: never accept a non-improvement
                break
            self.receipt("artifact_forged", nxt["id"],
                         {"parent": a["id"], "craft": nxt["last_craft"], "gain": round(nxt["total"] - a["total"], 6),
                          "total": nxt["total"], "compliant": nxt["compliant"]})
            lineage.append(nxt); a = nxt
        return lineage

def forge_demo():
    f = Forge()
    seed = artifact("weak-system", {"determinism": 0.62, "boundary": 0.58, "provenance": 0.30,
                                    "recovery": 0.40, "transparency": 0.66, "due_process": 0.55})
    lineage = f.build_better(seed)
    return {"lineage": lineage, "ledger": f.ledger, "verify": f.verify(),
            "passes": len(lineage) - 1, "start_total": lineage[0]["total"],
            "final_total": lineage[-1]["total"], "final_compliant": lineage[-1]["compliant"],
            "monotonic": all(lineage[i]["total"] > lineage[i-1]["total"] for i in range(1, len(lineage)))}

if __name__ == "__main__":
    r = forge_demo()
    if "--json" in sys.argv:
        print(json.dumps({k: v for k, v in r.items() if k != "lineage"} |
                         {"lineage": [{"gen": a["gen"], "total": a["total"], "compliant": a["compliant"], "craft": a["last_craft"]} for a in r["lineage"]]}, indent=2))
    else:
        print("HEPHAESTUS · THE FORGE — an artifact that builds better artifacts\n")
        for a in r["lineage"]:
            craft = f"  ·  craft: {a['last_craft'][1]} ({a['last_craft'][0]})" if a["last_craft"] else "  ·  (seed)"
            mark = "✓ CONSTITUTIONAL" if a["compliant"] else ""
            print(f"  gen {a['gen']}:  total {a['total']:.3f}  {mark}{craft}")
        print(f"\n  {r['passes']} passes · {r['start_total']:.3f} → {r['final_total']:.3f} · "
              f"strictly-improving: {r['monotonic']} · constitutional: {r['final_compliant']} · ledger: {r['verify']['ok']}")
