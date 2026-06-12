from hephaestus.mesh import seed_demo
import tempfile
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
    r=seed_demo(td)
    h=r["health"]
    assert h["nodes"]==4
    assert h["rule_sync"] is True
    assert h["violations"]==2
    assert h["overrides_approved"]==1
    assert h["ledger"]["ok"] is True
    assert r["bundle"]["exists"] is True
print("SELFTEST PASS")
