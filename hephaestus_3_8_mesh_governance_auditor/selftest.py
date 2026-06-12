from hephaestus.auditor import seed_demo
import tempfile
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
    r=seed_demo(td)
    h=r["health"]
    assert h["audits"]==2
    assert h["drift_found"]==1
    assert h["final_clean"] is True
    assert h["ledger"]["ok"] is True
    assert r["bundle"]["exists"] is True
print("SELFTEST PASS")
