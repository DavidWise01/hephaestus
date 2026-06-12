#!/usr/bin/env python3
"""HEPHAESTUS · status — re-run every module's selftest and print the honest scoreboard.

    python status.py            # human table
    python status.py --json     # machine readable

Classifies each hephaestus_* module as:
  PASS / FAIL  — has selftest.py, runs it live
  DATA-ONLY    — no python; a web+json scaffold (recorded result only, not executable here)
Stdlib only. Work in progress: see STATUS.md for the maturity ranking and roadmap.
"""
import os, sys, glob, json, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))

def classify(r):
    d = os.path.join(HERE, r)
    st = os.path.join(d, "selftest.py")
    if os.path.exists(st):
        try:
            cp = subprocess.run([sys.executable, "selftest.py"], cwd=d,
                                capture_output=True, text=True, timeout=120)
            return ("PASS", "") if cp.returncode == 0 else \
                   ("FAIL", ((cp.stdout + cp.stderr).strip().splitlines() or [""])[-1][:90])
        except Exception as e:
            return ("ERROR", str(e)[:80])
    py = glob.glob(os.path.join(d, "**", "*.py"), recursive=True)
    web = os.path.exists(os.path.join(d, "web", "index.html"))
    if not py:
        return ("DATA-ONLY", "web dashboard + json state, no executable selftest" if web else "data only")
    return ("PY-NO-SELFTEST", f"{len(py)} py files, no selftest.py")

def main():
    roots = sorted(d for d in os.listdir(HERE)
                   if d.startswith("hephaestus_") and os.path.isdir(os.path.join(HERE, d)))
    if os.path.exists(os.path.join(HERE, "forge", "selftest.py")):
        roots.append("forge")   # the heart: an artifact that builds better artifacts
    rows = [(r, *classify(r)) for r in roots]
    P = sum(s == "PASS" for _, s, _ in rows)
    F = sum(s in ("FAIL", "ERROR") for _, s, _ in rows)
    D = sum(s == "DATA-ONLY" for _, s, _ in rows)
    if "--json" in sys.argv:
        print(json.dumps({"total": len(rows), "pass": P, "fail": F, "data_only": D,
                          "modules": [{"module": r, "status": s, "note": n} for r, s, n in rows]}, indent=2))
        return
    glyph = {"PASS": "+", "FAIL": "x", "ERROR": "x", "DATA-ONLY": "·", "PY-NO-SELFTEST": "?"}
    print(f"HEPHAESTUS · STATUS — {P} pass · {F} fail · {D} data-only  (of {len(rows)} modules)\n")
    for r, s, n in rows:
        print(f"  {glyph.get(s,'?')} {r:48s} {s:14s} {n}")
    print("\ncode engine (0.0–2.8): runnable & green   |   tiers 3.x–4.0: web/json scaffolds (vision)")
    sys.exit(1 if F else 0)

if __name__ == "__main__":
    main()
